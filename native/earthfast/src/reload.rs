//! Scoped world-generation hot-reload planning and declarative rule hashing (`world_reload`).
//!
//! Validates canonical reload scopes (`"plans"`, `"roads"`, `"veg"`, `"surface"`, `"signs"`, `"nav"`), parses
//! declarative JSON rule overrides via `serde_json`, and hashes scoped epoch keys with `blake2` (`Blake2s256`).
//! Preserves `revisit.py`'s `PLAN_NEUTRAL` invariant: reloads that do not include `"plans"` (and rule overrides
//! restricted to `PLAN_NEUTRAL` switches) never invalidate road plan keys or evict cells from `PlanStore`.

use std::collections::BTreeMap;

use blake2::{Blake2s256, Digest};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

pub const SCOPE_PLANS: u32 = 1 << 0;
pub const SCOPE_ROADS: u32 = 1 << 1;
pub const SCOPE_VEG: u32 = 1 << 2;
pub const SCOPE_SURFACE: u32 = 1 << 3;
pub const SCOPE_SIGNS: u32 = 1 << 4;
pub const SCOPE_NAV: u32 = 1 << 5;

pub const CANONICAL_SCOPES: [(&str, u32); 6] = [
    ("plans", SCOPE_PLANS),
    ("roads", SCOPE_ROADS),
    ("veg", SCOPE_VEG),
    ("surface", SCOPE_SURFACE),
    ("signs", SCOPE_SIGNS),
    ("nav", SCOPE_NAV),
];

/// Switches that never alter road plans or cell facts (`server/revisit.py` `PLAN_NEUTRAL`).
pub const PLAN_NEUTRAL_KEYS: [&str; 10] = [
    "BNE_ROADSIGNS",
    "BNE_NL_ROADSIGNS",
    "BNE_WATERTIGHT",
    "BNE_CATENARY",
    "BNE_WEAR_STRIPS",
    "BNE_AI_TUNNELS",
    "BNE_RAIL_COLLIDE",
    "BNE_PRIORITY_STOPS",
    "BNE_CLIFF_WALLS",
    "BNE_DROP_RAILS",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReloadPlan {
    pub scopes: Vec<String>,
    pub mask: u32,
    pub invalidates_plans: bool,
    pub epoch: String,
    pub plans_epoch: Option<String>,
    pub evict_cells: Vec<(i32, i32, i32)>,
    pub full_digest: String,
    pub plans_digest: String,
}

fn hex16(bytes: &[u8]) -> String {
    bytes.iter().take(8).map(|b| format!("{b:02x}")).collect()
}

fn blake2s_hex16(parts: &[&[u8]]) -> String {
    let mut h = Blake2s256::new();
    for p in parts {
        h.update(p);
        h.update(b"\0");
    }
    hex16(&h.finalize())
}

pub fn is_plan_neutral_key(k: &str) -> bool {
    PLAN_NEUTRAL_KEYS.contains(&k)
}

/// Validates and canonicalizes a list of scope names into `(canonical_scopes, mask)`.
pub fn validate_scopes(scopes: &[String]) -> Result<(Vec<String>, u32), String> {
    if scopes.is_empty() {
        return Err("reload: scopes must not be empty".to_string());
    }
    let mut mask = 0u32;
    for raw in scopes {
        let s = raw.trim();
        let Some(&(_, bit)) = CANONICAL_SCOPES.iter().find(|&&(name, _)| name == s) else {
            return Err(format!(
                "reload: unknown scope {raw:?} (expected one of: plans, roads, veg, surface, signs, nav)"
            ));
        };
        mask |= bit;
    }
    let mut canonical = Vec::new();
    for &(name, bit) in &CANONICAL_SCOPES {
        if (mask & bit) != 0 {
            canonical.push(name.to_string());
        }
    }
    Ok((canonical, mask))
}

fn canonical_scalar(v: &serde_json::Value) -> Result<String, String> {
    match v {
        serde_json::Value::Null => Ok("null".to_string()),
        serde_json::Value::Bool(b) => Ok(if *b { "true".to_string() } else { "false".to_string() }),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.to_string())
            } else if let Some(u) = n.as_u64() {
                Ok(u.to_string())
            } else if let Some(f) = n.as_f64() {
                if !f.is_finite() {
                    return Err("reload: non-finite number in config".to_string());
                }
                let f = if f == 0.0 { 0.0 } else { f };
                Ok(format!("{f:.9}"))
            } else {
                Err("reload: unsupported number in config".to_string())
            }
        }
        serde_json::Value::String(s) => Ok(serde_json::to_string(s).unwrap_or_default()),
        serde_json::Value::Array(arr) => {
            let mut items = Vec::with_capacity(arr.len());
            for item in arr {
                if item.is_array() || item.is_object() {
                    return Err("reload: nested arrays/objects in config array are not allowed".to_string());
                }
                items.push(canonical_scalar(item)?);
            }
            Ok(format!("[{}]", items.join(",")))
        }
        serde_json::Value::Object(_) => Err("reload: nested objects in config are not allowed".to_string()),
    }
}

/// Parses a declarative JSON rule/switch object and returns `(full_digest, plans_digest)`.
/// `PLAN_NEUTRAL` keys are excluded from `plans_digest` so toggling them never invalidates road plan caches.
pub fn parse_config_digests(config_json: Option<&str>) -> Result<(String, String), String> {
    let raw = config_json.unwrap_or("").trim();
    if raw.is_empty() {
        let empty = blake2s_hex16(&[b"cfg:v1"]);
        return Ok((empty.clone(), empty));
    }
    let val: serde_json::Value =
        serde_json::from_str(raw).map_err(|e| format!("reload: invalid config JSON: {e}"))?;
    let serde_json::Value::Object(map) = val else {
        return Err("reload: config JSON must be an object".to_string());
    };
    let mut sorted = BTreeMap::new();
    for (k, v) in map {
        let k_trim = k.trim();
        if k_trim.is_empty() || !k_trim.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-' || b == b'.') {
            return Err(format!("reload: invalid config key {k:?}"));
        }
        sorted.insert(k_trim.to_string(), canonical_scalar(&v)?);
    }
    let mut full_h = Blake2s256::new();
    let mut plans_h = Blake2s256::new();
    full_h.update(b"cfg:v1\0");
    plans_h.update(b"cfg:v1\0");
    for (k, v) in &sorted {
        let entry = format!("{k}={v}\0");
        full_h.update(entry.as_bytes());
        if !is_plan_neutral_key(k) {
            plans_h.update(entry.as_bytes());
        }
    }
    Ok((hex16(&full_h.finalize()), hex16(&plans_h.finalize())))
}

fn validate_and_sort_cells(cells: &[(i32, i32, i32)]) -> Result<Vec<(i32, i32, i32)>, String> {
    let mut out = Vec::with_capacity(cells.len());
    for &(z, x, y) in cells {
        if !(0..=24).contains(&z) {
            return Err(format!("reload: cell zoom {z} out of range 0..=24"));
        }
        let lim = 1i64 << z;
        if (x as i64) < 0 || (x as i64) >= lim || (y as i64) < 0 || (y as i64) >= lim {
            return Err(format!("reload: cell ({z}, {x}, {y}) out of bounds for zoom {z}"));
        }
        out.push((z, x, y));
    }
    out.sort_unstable();
    out.dedup();
    Ok(out)
}

/// Computes the deterministic reload plan for a `world_reload` request.
pub fn compute_reload_plan(
    scopes: &[String],
    clear_cells: Option<&[(i32, i32, i32)]>,
    active_cells: Option<&[(i32, i32, i32)]>,
    config_json: Option<&str>,
    serial: u64,
) -> Result<ReloadPlan, String> {
    let (canonical_scopes, mask) = validate_scopes(scopes)?;
    let (full_digest, plans_digest) = parse_config_digests(config_json)?;
    let invalidates_plans = (mask & SCOPE_PLANS) != 0;
    let clear_validated = match clear_cells {
        Some(c) => validate_and_sort_cells(c)?,
        None => Vec::new(),
    };
    let active_validated = match active_cells {
        Some(c) => validate_and_sort_cells(c)?,
        None => Vec::new(),
    };
    let evict_cells = if !invalidates_plans {
        Vec::new()
    } else if !clear_validated.is_empty() {
        clear_validated
    } else {
        active_validated
    };
    let serial_bytes = serial.to_le_bytes();
    let mask_bytes = mask.to_le_bytes();
    let epoch = blake2s_hex16(&[b"epoch:v1", &serial_bytes, &mask_bytes, full_digest.as_bytes()]);
    let plans_epoch = if invalidates_plans {
        Some(blake2s_hex16(&[b"plans:v1", &serial_bytes, plans_digest.as_bytes()]))
    } else {
        None
    };
    Ok(ReloadPlan {
        scopes: canonical_scopes,
        mask,
        invalidates_plans,
        epoch,
        plans_epoch,
        evict_cells,
        full_digest,
        plans_digest,
    })
}

#[pyfunction]
pub fn reload_scope_mask(scopes: Vec<String>) -> PyResult<u32> {
    let (_, mask) = validate_scopes(&scopes).map_err(PyValueError::new_err)?;
    Ok(mask)
}

#[pyfunction]
#[pyo3(signature = (config_json=None))]
pub fn reload_config_digests(config_json: Option<&str>) -> PyResult<(String, String)> {
    parse_config_digests(config_json).map_err(PyValueError::new_err)
}

#[pyfunction]
#[pyo3(signature = (scopes, clear_cells=None, active_cells=None, config_json=None, serial=1))]
pub fn reload_plan<'py>(
    py: Python<'py>,
    scopes: Vec<String>,
    clear_cells: Option<Vec<(i32, i32, i32)>>,
    active_cells: Option<Vec<(i32, i32, i32)>>,
    config_json: Option<&str>,
    serial: u64,
) -> PyResult<Bound<'py, PyDict>> {
    let plan = compute_reload_plan(
        &scopes,
        clear_cells.as_deref(),
        active_cells.as_deref(),
        config_json,
        serial,
    )
    .map_err(PyValueError::new_err)?;
    let d = PyDict::new(py);
    d.set_item("scopes", PyList::new(py, &plan.scopes)?)?;
    d.set_item("mask", plan.mask)?;
    d.set_item("invalidates_plans", plan.invalidates_plans)?;
    d.set_item("epoch", &plan.epoch)?;
    d.set_item("plans_epoch", plan.plans_epoch.as_deref())?;
    d.set_item("evict_cells", PyList::new(py, &plan.evict_cells)?)?;
    d.set_item("full_digest", &plan.full_digest)?;
    d.set_item("plans_digest", &plan.plans_digest)?;
    Ok(d)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(reload_scope_mask, m)?)?;
    m.add_function(wrap_pyfunction!(reload_config_digests, m)?)?;
    m.add_function(wrap_pyfunction!(reload_plan, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_scopes_and_rejections() {
        let (sc, mask) = validate_scopes(&["veg".into(), "roads".into(), "veg".into()]).unwrap();
        assert_eq!(sc, vec!["roads".to_string(), "veg".to_string()]);
        assert_eq!(mask, SCOPE_ROADS | SCOPE_VEG);
        assert!(validate_scopes(&[]).is_err());
        assert!(validate_scopes(&["roads".into(), "bogus".into()]).is_err());
    }

    #[test]
    fn plan_neutral_config_preserves_plans_digest() {
        let (f0, p0) = parse_config_digests(Some(r#"{"BNE_ROADSIGNS": false}"#)).unwrap();
        let (f1, p1) = parse_config_digests(Some(r#"{"BNE_ROADSIGNS": true, "BNE_CATENARY": "1"}"#)).unwrap();
        let (_, p_empty) = parse_config_digests(None).unwrap();
        assert_ne!(f0, f1, "full digest reflects PLAN_NEUTRAL switch changes");
        assert_eq!(p0, p1, "plans digest ignores PLAN_NEUTRAL switches");
        assert_eq!(p0, p_empty, "only PLAN_NEUTRAL switches equals empty plan digest");

        let (_, p_grade) = parse_config_digests(Some(r#"{"BNE_GRADE_GUARD": "on"}"#)).unwrap();
        assert_ne!(p0, p_grade, "non-neutral switch changes plans digest");
    }

    #[test]
    fn non_plan_reload_never_evicts_or_bumps_plans() {
        let active = vec![(14, 8400, 5900), (14, 8399, 5900)];
        let clear = vec![(14, 8400, 5900)];
        let plan = compute_reload_plan(
            &["roads".into(), "veg".into(), "signs".into()],
            Some(&clear),
            Some(&active),
            Some(r#"{"BNE_WEAR_STRIPS": true}"#),
            1,
        )
        .unwrap();
        assert!(!plan.invalidates_plans);
        assert!(plan.plans_epoch.is_none());
        assert!(plan.evict_cells.is_empty());
        assert_eq!(plan.scopes, vec!["roads", "veg", "signs"]);
    }

    #[test]
    fn plans_scope_evicts_targeted_cells_deterministically() {
        let active = vec![(14, 8401, 5900), (14, 8400, 5900)];
        let clear = vec![(14, 8405, 5902), (14, 8402, 5901), (14, 8405, 5902)];
        let p_targeted = compute_reload_plan(&["plans".into(), "roads".into()], Some(&clear), Some(&active), None, 2).unwrap();
        assert!(p_targeted.invalidates_plans);
        assert!(p_targeted.plans_epoch.is_some());
        assert_eq!(p_targeted.evict_cells, vec![(14, 8402, 5901), (14, 8405, 5902)]);

        let p_active = compute_reload_plan(&["plans".into()], None, Some(&active), None, 2).unwrap();
        assert_eq!(p_active.evict_cells, vec![(14, 8400, 5900), (14, 8401, 5900)]);
    }
}
