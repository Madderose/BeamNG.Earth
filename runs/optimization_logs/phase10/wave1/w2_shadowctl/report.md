# Phase 10 Wave 1 — W2 (`shadowctl.lua`) Implementation Report

## 1. Summary of Changes (`file:line`)

### [`mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua)
- **R2 — Hot-path scans removed (`L81–L90`)**:
  - Deleted `M.syncTreeDatablocks()` (datablock-set scan) and `M.sweepEmptyForests()` (`getItems()` table allocation across up to 160 `Forest`s), along with `NEAR_TREE_NULL_PX`, `FAR_TREE_NULL_PX`, `seenTreeTypes`, `lastForestCount`, and `forestUpdateTick`.
  - [`M.onForestTileUpdated`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua#L89) is now a direct O(1) alias of [`M.noteBurst`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua#L84-L86) (`trees.lua` owns `Forest` hide/unhide and `shadowNullDetailSize`).
- **R4 — Runtime material/skin remaps removed (`L94–L115`)**:
  - Deleted `ensureRoadMaterials()`, `ensureFarMaterial()` (`bngEarthFar_v3` already sets `"castShadows": false` in `levels/beamng_earth/art/shapes/beamngEarth/main.materials.json:18`), `M.GROUND_NO_SHADOW_MATS`, `M.BLD_CLONE_SUFFIXES`, `COPY_MAT_FIELDS`, and `M.BLD_NOSHADOW_SKIN`.
  - [`M.excludeObject(obj, kind)`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua#L94-L115) preserves offline stub-table field writes (`isRenderShadowEnabled = 'false'`, `castShadows = '0'`) for `'far'` / `'road_static'` without C++ userdata no-ops or `skin` remaps, and hides `'forest_empty'` objects.
- **R3 — Burst-gated shadow distance profile & diagnostics (`L20–L40`, `L135–L211`)**:
  - Added module-level diagnostics table [`M.state`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua#L35-L40) (`{ scale, burstBlend, holdS, triggers }`), updated in place with zero per-frame allocation.
  - [`M.applyGlobalProfile(speedMps, gov, dtReal)`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua#L150-L211) triggers **only** on real structural work: `burstPending` (`M.noteBurst()`) OR `(gov.sceneStructCount or 0) > 0` OR `gov.burst == true`. Plain governor units (`frameUnits > 0`, `spent > 0`) do not trigger tightening.
  - Suppresses tightening when `gov.loading == true` or `not M.BURST_ENABLED` (keeps base velocity-adaptive profile `0.45 -> 0.25` between `20` and `60 m/s`).
  - Envelope: instant attack (`<= 2` frames, reaches `M.BURST_SCALE = 0.22` on the trigger frame before `RenderShadows`), holds at full burst scale for `M.BURST_HOLD_S = 1.05 s` (`>= 1.0 s`), then releases linearly and monotonically over `M.BURST_RELEASE_S = 0.60 s` (`>= 0.5 s`). Re-triggers during hold extend the hold; re-triggers during release immediately re-attack.
  - Keeps `M.SCALE_EPS = 0.005` quantization on `PSSMLightShadowMap.sdsmMaxDistanceScale` and `lastSplitCastersEnabled = false`.
- **Setting gate & 1 Hz poll (`L24–L27`, `L117–L133`)**:
  - Exposes `M.BURST_ENABLED = true` and `M.BURST_SCALE = 0.22` (clamped to `[0.10, 0.45]`), and polls `beamngEarth/settings` at most once per second (`M.SETTINGS_POLL_S = 1.0`).

### [`mod/beamng_earth/lua/ge/extensions/beamngEarth/settings.lua`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/settings.lua)
- **`L72–L73`, `L81`**: Added hidden persisted settings `shadowBurst` (`bool`, default `true`) and `shadowBurstScale` (`number`, default `0.22`, min `0.10`, max `0.45`) to `M.SCHEMA` and `M.HIDDEN` (no UI changes).
- **`L270–L271`, `L284–L285`**: Wired `M.APPLY.shadowBurst` and `M.APPLY.shadowBurstScale` (and `M.applyAll()`) to update `shadowctl.BURST_ENABLED` and `shadowctl.BURST_SCALE`.

### [`mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua)
- **`L66`**: Cached `local shadowctl = require('beamngEarth/shadowctl')` as a module-level upvalue.
- **`L1603`**: Replaced per-frame `require('beamngEarth/shadowctl').applyGlobalProfile(...)` in `onPreRender` with `shadowctl.applyGlobalProfile((pl and pl.speed) or 0, gov, dtReal)`.

### [`mod/tests/test_shadowctl.lua`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_shadowctl.lua)
- **`L1–L222`**: Removed obsolete tests for deleted functions (`syncTreeDatablocks`, `sweepEmptyForests`, `bne_noshad_*` cloning / `skin` remap) and added coverage for all R2/R3/R4 requirements and `settings.lua` integration.

---

## 2. Test Results

Executed from `mod/tests` with `..\..\vendor\luajit\luajit.exe`:
- `test_shadowctl.lua`: **113 passed, 0 failed**
  - Plain governor units (`frameUnits > 0`, `sceneStructCount = 0`, `burst = false`) -> stays at `0.45`.
  - Structural trigger (`sceneStructCount > 0`, `gov.burst = true`, `noteBurst()`, `onForestTileUpdated()`) -> reaches `0.22` within `<= 2` frames.
  - Hold lasts `>= 1.0 s` (`60` frames at `60 Hz` remain at `0.22`).
  - Release takes `>= 0.5 s` (`36` frames at `60 Hz`) and is strictly monotonic back to `0.45`.
  - Re-trigger during hold extends hold; re-trigger during release re-attacks to `0.22`.
  - `gov.loading = true` -> no tightening (`0.45`).
  - `BURST_ENABLED = false` / `settings.set('shadowBurst', false)` -> no tightening; `settings.get` polled at most once per second.
  - `onForestTileUpdated` is O(1) with zero `scenetree` or datablock calls.
- `test_settings.lua`: **148 passed, 0 failed**
- `test_core_stubbed.lua`: **263 passed, 3 failed** (exact match to baseline `scratch/p10w1_baseline_lua_failures.txt`; zero new failures).

---

## 3. How to Flip the Setting Live (MCP / Console)

Via persisted settings (`beamngEarth_settings`):
```powershell
# Disable burst shadow tightening:
python tools/mcp.py lua "beamngEarth_settings.set('shadowBurst', false)"

# Re-enable and set custom burst scale (clamped to 0.10..0.45):
python tools/mcp.py lua "beamngEarth_settings.set('shadowBurst', true); beamngEarth_settings.set('shadowBurstScale', 0.18)"
```

Or directly on the `shadowctl` module constants + inspect live state:
```powershell
python tools/mcp.py lua "local s = require('beamngEarth/shadowctl'); s.BURST_ENABLED = false; return s.state"
```

---

## 4. Risks & Mitigations
- **Sustained structural streaming**: During continuous heavy tile/tree streaming, `sdsmMaxDistanceScale` stays at `0.22` until `1.05 s` after the last structural mutation, then ramps back over `0.60 s`. Because hold is `>= 1.0 s` and non-structural governor work (`retex`, `crossover`, etc.) does not trigger tightening, shadow distance never pumps on calm or texture-only frames.

## 5. Cross-Task Requests
- **W1 (`governor.lua`)**: Ensure `gov.sceneStructCount` is reset per frame and incremented only for `SCENE_STRUCT_KINDS`, and `gov.burst` / `gov.loading` remain exposed on `gov` (per the Wave 1 interface contract).
- **W3 (`trees.lua`)**: Call `shadowctl.noteBurst()` (via cached module upvalue) when mutating a `Forest`, set `shadowNullDetailSize` directly in `trees.itemType()`, and hide/unhide `Forest`s in `releaseForest()` / `forest()`.

STATUS_UPDATE: DONE (100%)
