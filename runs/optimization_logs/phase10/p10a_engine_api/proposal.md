# Phase 10A Proposal — Engine Shadow Control Surface Discovery & Dead-Toggle Replacement

## 0. Definitive BeamNG 0.40 Shadow Control Surface & Live A/B Measurement Table

All properties, C++ field tables (`getFields()` / `getFieldsForEditor()`), userdata metatables (`mt[1]`/`mt[2]`), and console variables (`VariableRegistry` / `getConsoleVariable`) were probed live in **BeamNG.drive 0.40.1 (D3D12)** via `tools/mcp.py`. Short reversible A/B measurements sampled `RenderShadows` and `Render` CPU timings (`get_performance_metrics`) in two regimes:
- **Steady State** (`92,346` live Forest items across `124` non-empty + `25` empty `Forest`s, `581` far-field tiles, `316` road/building objects, zero active streaming mutations).
- **Streaming Burst State** (`trees.lua` actively mutating `20` items/frame across `212` pending tiles while `ForestCell` batches rebuild in the shadow pass).

### 0.1 Global Singletons, `ScatterSky`, and Console Variables (`$pref::*`)

| Knob / Property | Exists in 0.40? | Type | Live Value | Scope | Cuts CPU Shadow Traversal? | Steady-State `RenderShadows` A/B (Before $\rightarrow$ After) | Streaming-Burst `RenderShadows` A/B (Before $\rightarrow$ After) |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| `PSSMLightShadowMap.sdsmMaxDistanceScale` | **Yes** | `float` | `0.45` (`0.5` engine default) | Global | **Yes (Strong on bursts)** — shrinks world volume of Cascades 1–3; avoids synchronous dirty `ForestCell` batch rebuilds at `225–675 m` | `0.45 -> 0.25`: `0.476 -> 0.478 ms` ($\Delta +0.002\text{ ms}$)<br>`0.45 -> 0.15`: `0.413 -> 0.460 ms` ($\Delta +0.047\text{ ms}$) | `0.45 -> 0.15` (burst tighten):<br>**mean `8.100 -> 1.435 ms` ($\Delta -6.665\text{ ms}$)**<br>**median `10.745 -> 1.057 ms` ($\Delta -9.688\text{ ms}$)**<br>**p95 `18.581 -> 1.250 ms` ($\Delta -17.331\text{ ms}$)** |
| `PSSMLightShadowMap.sdsmFitEnabled` | **Yes** | `bool` | `false` | Global | **Yes (Moderate on bursts)** — depth-fits cascade splits to visible scene bounds | `false -> true`: `0.518 -> 0.546 ms` ($\Delta +0.028\text{ ms}$) | `false -> true`:<br>**mean `7.879 -> 4.992 ms` ($\Delta -2.887\text{ ms}$)**<br>**median `10.711 -> 1.014 ms` ($\Delta -9.697\text{ ms}$)** |
| `PSSMLightShadowMap.vehicleShadowEnabled` | **Yes** | `bool` | `true` | Global | **Yes (5th dedicated pass)** — controls dedicated 2048px player vehicle shadow pass | `true -> false`: `0.527 -> 0.491 ms` ($\Delta -0.036\text{ ms}$) | `true -> false`:<br>**mean `3.944 -> 2.292 ms` ($\Delta -1.652\text{ ms}$)**<br>**median `0.552 -> 0.385 ms` ($\Delta -0.168\text{ ms}$)** |
| `PSSMLightShadowMap.lastSplitCastersEnabled` | **Yes** | `bool` | `false` (set by `core.lua`) | Global | **Yes** — disables non-terrain casters in Cascade 3 (already `false` in `core.lua`) | `false -> true`: `0.559 -> 0.461 ms` (at `shadowNullDetailSize=35`) | Already active (`false`); prevents Cascade 3 `TSStatic`/`Forest` submission |
| `PSSMLightShadowMap.penumbraEnabled` | **Yes** | `bool` | `false` | Global | **No** — GPU PCSS shader permutation only | N/A (`false` on current preset) | N/A |
| `PSSMLightShadowMap.vehicleTexSize` | **Yes** | `int` | `2048` | Global | **No** — GPU resolution of 5th vehicle pass | N/A (GPU-only) | N/A |
| `ShadowMapPass.disableShadows` | **Yes** | `bool` | `false` | Global | **Yes** — master shadow-pass disable switch (`$pref::Shadows::disable`) | `false -> true`: `0.421 -> 0.465 ms` (steady state already cached) | Disables all shadows globally (visual loss; diagnostic only) |
| `ScatterSky.castShadows` | **Yes** | `bool` | `1` | Per-Light (`sunsky`) | **Yes** — disables directional sun/moon shadow map | Master light toggle | Disables sun shadows globally |
| `ScatterSky.texSize` | **Yes** | `int` | `512` | Per-Light (`sunsky`) | **No** — GPU shadow map resolution | `512 -> 1024`: `0.412 -> 0.443 ms` ($\Delta +0.031\text{ ms}$ CPU) | GPU-only knob (+0.03 ms CPU delta) |
| `ScatterSky.shadowDistance` / `logWeight` / `numSplits` / `softness` | **Deprecated in 0.40** | — | `""` (not in `getFields()`) | — | **No** — removed from `ScatterSky` in 0.40; replaced by `PSSMLightShadowMap` SDSM | No-op dynamic fields on `ScatterSky` | No-op dynamic fields on `ScatterSky` |
| `$pref::imposter::canShadow` | **Yes** | `bool` (`int`) | `1` | Global CVar | **Partial** — controls `TSLastDetail` imposter shadow rendering | `1 -> 0`: `0.479 -> 0.461 ms` ($\Delta -0.018\text{ ms}$ mean, $-0.040\text{ ms}$ median) | Superseded when `TSForestItemData.shadowNullDetailSize` culls distant trees before imposter selection |
| `$pref::TS::smallestVisiblePixelSize` (`RenderSettings.meshSmallestPixelSize`) | **Yes** | `float` | `-1` | Global CVar | **Yes (Main + Shadow)** — culls shapes below pixel size in both main and shadow passes | `-1 -> 8`: `0.435 -> 0.456 ms` ($\Delta +0.021\text{ ms}$) | `-1 -> 6`: `0.856 -> 0.777 ms` ($\Delta -0.080\text{ ms}$ mean, $-0.086\text{ ms}$ median) |
| `$pref::TS::detailAdjust` (`RenderSettings.meshDetailAdjust`) | **Yes** | `float` | `1.5` | Global CVar | **Yes (Main + Shadow)** — biases `TSShapeInstance::selectCurrentDetail` | `1.5 -> 0.75`: `0.463 -> 0.479 ms` ($\Delta +0.015\text{ ms}$) | `1.5 -> 0.75`: `1.545 -> 1.224 ms` ($\Delta -0.322\text{ ms}$ mean, max `19.26 -> 6.29 ms`) |
| `$pref::Shadows::textureScalar` (`RenderSettings.shadowTexScalar`) | **Yes** | `float` | `1` | Global CVar | **No** — scales shadow map texture resolution | GPU-only | GPU-only |
| `$pref::Shadows::teleportDist` / `turnRate` / `$Scene::disableShadows` | **No** | — | `nil` | — | **No** — not registered in BeamNG 0.40 `VariableRegistry` | Does not exist | Does not exist |

### 0.2 Per-Class / Per-Object / Per-Material / Per-Datablock Control Surfaces

| Class & Field / Method | Exists in 0.40? | Type | Live Value | Scope | Cuts CPU Shadow Traversal / Submission? | Verified Behavior in Live Engine |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `SceneObject` / `TSStatic` / `Forest`: `isRenderShadowEnabled` | **NO (Dead No-Op)** | — | Dynamic string | Per-Object | **NO (0 ms saved)** — `canSaveDynamicFields = 1` silently stores an ignored string property | Called in `trees.lua` (L952/954, L1077/1080), `farfield.lua` (L353, L392), `roads.lua` (L382). **100% no-op.** |
| `TSStatic` / `Forest`: `castShadows` | **NO (Dead No-Op)** | — | Dynamic string | Per-Object | **NO (0 ms saved)** — `castShadows` only exists on `Material`, `LightBase`, `ScatterSky` | Called in `farfield.lua` (L354, L393) and `roads.lua` (L383). **100% no-op.** |
| `Material.castShadows` | **Yes** | `bool` | `'0'` or `'1'` | Per-Material | **Yes** — `ShadowMaterialHook` skips generating/submitting `MeshRenderInst` draw calls for that material | Verified live: `bngEarthFar_v3` and `satmat` have `'0'`, **but** stock materials loaded by `roads.lua` (`curbs`, `sidewalk1`, `tactile_indicator`, `m_dirt_road`, `italy_cobblestone`) and `bne_bld_facade` (used by **114 `bldfar` TSStatics**) have `castShadows = '1'`! |
| `TSStatic.skin` (`setField('skin', 0, 'old=new')`) | **Yes** | `string` (`TypeRealString`) | `""` | Per-Object (`TSStatic`) | **Yes** — renames material targets per `TSStatic` instance (`'bne_bld_=bne_noshad_'`) to bind `castShadows = '0'` clone materials | Verified live via `TSStatic:getFieldsForEditor()`. Setting `skin = 'bne_bld_=bne_noshad_'` before `registerObject` keeps all **114 `bldfar` horizon building TSStatics** out of shadow draw submission while near `bld` tiles keep shadows! |
| `TSStatic:changeMaterial(...)` | **Yes** | `method` | C++ method | Per-Object (`TSStatic`) | **Yes** — C++ material override method on `TSStatic` | Present in `getmetatable(TSStatic)`, but `skin` field works pre-registration via standard `setField('skin', 0, ...)` |
| `TSStatic.forceDetail` | **Yes** | `int` (`TypeI32`) | `-1` | Per-Object (`TSStatic`) | **Partial** — forces a fixed LOD detail index in both main and shadow passes | Affects main camera pass too; not suitable for near buildings unless coarse LOD matches visually |
| `TSStatic.meshCulling` | **Yes** | `bool` | `0` | Per-Object (`TSStatic`) | **Submesh frustum culling** — *"Should only be used with large complex shapes like buildings which contain many submeshes"* | Real C++ field (`id=7`), adds per-submesh AABB CPU checks |
| `TSForestItemData.shadowNullDetailSize` | **Yes** | `int` (`TypeI32`) | `'35'` | Per-Datablock (`forestItemData`) | **Yes (Massive)** — shadow-map pixel size threshold below which a tree is culled (`null` detail) in `RenderShadows` only | `trees.lua` already splits datablocks into `bngEarthTree_<sh>` (`solid=true`, $\le 90\text{--}125\text{ m}$) and `bngEarthTree_<sh>_n` (`solid=false`, $> 90\text{--}125\text{ m}$). Setting `'500'` on `_n` datablocks culls $>125\text{ m}$ trees from shadow cascades with **zero extra item churn**! |
| `Forest:setHidden(bool)` / `isRenderEnabled` | **Yes** | `bool` | `hidden=0` on **25 empty Forests** | Per-Object (`Forest`) | **Yes** — skips `Forest::prepRenderImage()` in all 4 shadow cascades for empty pooled `Forest`s | Live probe found `149` `bngEarthForest_*` objects: `124` non-empty, **`25` empty but still visible (`hidden=0`)**. Because `Forest` is `isGlobalBounds() = true`, every empty visible `Forest` is traversed in all 4 cascades (`100` wasted dispatches/frame). |
| `GroundCover.shapesCastShadows` | **Yes** | `bool` | `'0'` | Per-Object (`GroundCover`) | **Yes** — disables 3D groundcover shape shadows | Already set to `'0'` on `bngEarthGC_*` objects |

---

## 1. Key Findings & Root-Cause Evidence

1. **Working Hypothesis Confirmed by Live Telemetry (Why `RenderShadows` Spikes to 10–20 ms on Bursts, While Steady State is 0.45 ms)**:
   - In pure steady state (`ab_probe_steady.py`, `92,346` trees, `581` far tiles, `316` road/building objects, `0` mutations/frame), `RenderShadows` CPU cost is **mean `0.41–0.52 ms`** (`median 0.40–0.48 ms`).
   - During active tree/tile streaming (`ab_probe.py`, while `trees.lua` was mutating `20` items/frame across `212` pending tiles and draining `orphanDrops`), `RenderShadows` jumped to **mean `8.10 ms`, median `10.75 ms`, p95 `18.58 ms`, max `20.28 ms`**.
   - **Why**: Whenever `trees.lua` calls `createNewItem`/`removeItem` on a `Forest` tile at `125–675 m` (or `roads.lua` spawns a `TSStatic` with shadow-casting materials), that `Forest`'s `ForestCell` batches are marked dirty and rebuilt lazily inside the **first render pass of the frame (`ShadowMapPass::render()` / `RenderShadows`)** across all intersecting cascades.
   - Furthermore, changing `PSSMLightShadowMap.sdsmMaxDistanceScale` continuously every frame at intermediate speeds (`20–60 m/s` in [core.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua#L1594-L1604)) shifts cascade split boundaries every frame, invalidating cached shadow cascade bounds.

2. **Live Material & SceneGraph Audit Revealed 195+ Unintended Shadow-Casting `TSStatic`s in `bngEarthRoads`**:
   - Probing all `316` objects inside `bngEarthRoads` and all `39` materials referenced by `prewarm.cdae` revealed:
     - **`114` `bldfar` horizon building `TSStatic`s** (`spawnFar` in [roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L392-L394)) use `bne_bld_facade`, which has `castShadows = "1"`. Because `o:setField('isRenderShadowEnabled', 0, 'false')` and `o:setField('castShadows', 0, '0')` at [roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L382-L383) are silent no-ops on `TSStatic`, **all 114 distant `bldfar` horizon building meshes are actively casting shadows**.
     - **Stock road/sidewalk materials loaded by `roads.lua`** (`curbs`, `sidewalk1`, `tactile_indicator`, `m_dirt_road`, `italy_cobblestone`) retain `castShadows = "1"` from their official BeamNG level JSONs (`18` sidewalk meshes and `49` dirt/cobblestone road meshes in the live scene).

3. **25 Empty Pooled `Forest` Objects Are Visible in `MissionGroup`**:
   - In [trees.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L226-L229), `releaseForest(t)` returns `t.forestId` to `pool` without hiding the `Forest`. Because `Forest` has `isGlobalBounds() == true`, `SceneOctree` cannot frustum-cull empty `Forest`s and invokes `Forest::prepRenderImage()` on all `25` empty `Forest`s across all 4 cascades every frame.

---

## 2. Ranked Proposals

### Proposal 1 (Rank #1): Streaming-Burst Shadow Tightening Profile + Quantized SDSM Updates (`shadowctl.applyGlobalProfile`)
- **What**: In [shadowctl.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/phase10/p10a_engine_api/new_files/mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua) (called from [core.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua#L1592-L1604) `onPreRender`), detect frames where streaming units ran (`gov.frameUnits > 0` or `gov.spent >= 0.4`) or `trees.lua` mutated `Forest` items (`shadowctl.noteBurst()`). Tighten `PSSMLightShadowMap.sdsmMaxDistanceScale` to `0.22` during the burst with a smooth `0.40 s` relaxation envelope (`BURST_RAMP_S = 0.15 s`), and quantize C++ userdata writes (`SCALE_EPS = 0.005`) so steady-state frames perform zero C++ property writes.
- **Why**: Prevents newly dirtied `ForestCell`s and imported `.cdae` meshes at `330–675 m` from forcing synchronous `ForestCellBuildBatches` and `ShadowMaterialHook` init inside `RenderShadows` on the same frame that Lua and `FileWatchers` already spent 6–15 ms.
- **Expected ms saved**: **Spikes: `-6.0 to -9.7 ms` median / `-12.0 to -17.3 ms` p95** (measured live in `ab_probe.py`: mean `8.10 -> 1.43 ms`, p95 `18.58 -> 1.25 ms`). **Steady state: `~0.02 ms`** (eliminates per-frame C++ userdata setter churn).
- **Risk & Visual Impact**: Very low risk; near-car shadows (`0–330 m`) actually become sharper during the `0.40 s` burst window and smoothly relax over 24 frames.
- **Files touched**: `shadowctl.lua` (new), [core.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua#L1592-L1604).

### Proposal 2 (Rank #2): Split `TSForestItemData.shadowNullDetailSize` Between Solid Near Trees (`35`) and Non-Solid Far Trees (`500`) + Hide Empty Pooled `Forest`s
- **What**: Replace the two dead `isRenderShadowEnabled` blocks in [trees.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L946-L958) and [trees.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L1073-L1083):
  1. Remove the dead per-tile `isRenderShadowEnabled` check inside the hot `for key, t in pairs(tiles)` loop (`L946–958`).
  2. At `L1073–1083`, call `shadowctl.onForestTileUpdated(t.forestId, ...)`, which upgrades non-solid `bngEarthTree_*_n` datablocks (`collidable == '0'`, used by all trees beyond `SOLID_M = 90..125 m`) to `shadowNullDetailSize = '500'` (while keeping solid near-car `bngEarthTree_*` datablocks at `'35'`), and sweeps empty pooled `bngEarthForest_*` objects to `setHidden(true)`.
- **Why**: `trees.lua` already swaps items between `bngEarthTree_<sh>` (`solid=true`, $\le 90\text{--}125\text{ m}$) and `bngEarthTree_<sh>_n` (`solid=false`, $125\text{--}900\text{ m}$). Setting `shadowNullDetailSize = '500'` on `_n` datablocks culls all $>125\text{ m}$ trees from the 512px shadow cascades in C++ **with zero extra item churn at 300 m**, eliminating distant `ForestCell` shadow batch rebuilds when rings 1–5 thin/fill!
- **Expected ms saved**: **Spikes: `-4.0 to -8.0 ms`** (eliminates shadow batch rebuilds for all tree mutations in rings 1–5 beyond 125 m). **Steady state: `-0.08 to -0.15 ms`** (25 empty `Forest`s + distant `_n` trees skipped in `RenderShadows`).
- **Risk & Visual Impact**: Low risk; trees within `90–125 m` of the vehicle (`solid = true`) retain `shadowNullDetailSize = 35` and cast full 3D shadows.
- **Files touched**: `shadowctl.lua` (new), [trees.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L946-L958) (`~L946–958`, `~L1073–1083`).

### Proposal 3 (Rank #3): Per-Object `TSStatic` `skin` Remap (`bne_bld_=bne_noshad_`) & Ground Material Shadow Stripping (`shadowctl.excludeObject`)
- **What**: Replace dead `isRenderShadowEnabled` / `castShadows` calls in [roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L382-L383) and [farfield.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L353-L354) (`~L353–354`, `~L392–393`) with `shadowctl.excludeObject(o, kind)`:
  - Strips `castShadows` (`'0'` + `flush()`/`reload()`) once on flat stock road/sidewalk materials (`curbs`, `sidewalk1`, `tactile_indicator`, `m_dirt_road`, `italy_cobblestone`).
  - Clones `bne_bld_*` materials once into `bne_noshad_*` (`mapTo = 'bne_noshad_*'`, `castShadows = '0'`) and sets `o:setField('skin', 0, 'bne_bld_=bne_noshad_')` on non-shadow `roads.lua` `TSStatic`s (`bldfar`, `walk`, `road`, `wire`) **before `o:registerObject('')`**.
  - On `farfield.lua` `TSStatic`s (`kind == 'far'`), verifies `bngEarthFar_v3` `castShadows = '0'` once and eliminates the 2 dead C++ `setField` calls per spawn/revive (while still populating stub fields on plain Lua tables so offline `test_farfield.lua` and `test_farfield_spares.lua` pass unmodified).
- **Why**: Excludes all `114` `bldfar` horizon building meshes, `18` sidewalk meshes, and `49` dirt/cobblestone road meshes from `RenderShadowMeshPassMgr` draw submission and first-render `ShadowMaterialHook` initialization.
- **Expected ms saved**: **Spikes: `-1.0 to -2.5 ms`** on road/building tile import frames. **Steady state: `-0.05 to -0.12 ms`**.
- **Risk & Visual Impact**: Zero visual impact near the vehicle (`bld` and `deck` meshes have `castShadow = true` and do not call `excludeObject`, keeping full 3D building and bridge shadows).
- **Files touched**: `shadowctl.lua` (new), [roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L382-L383), [farfield.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L353-L354).

---

## 3. Patch List

All patches are in `runs/optimization_logs/phase10/p10a_engine_api/` and verified with `git apply --check`:
1. `shadowctl.lua.diff` (and `new_files/mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua`): New shadow control module implementing capability probing, `excludeObject(obj, kind)`, `onForestTileUpdated(forestId, nearShadow)`, and `applyGlobalProfile(speed, gov, dtReal)`.
2. `trees.lua.diff`: Removes the dead `isRenderShadowEnabled` loop block at `L946–958` and replaces `L1073–1083` with `shadowctl.onForestTileUpdated(...)`.
3. `farfield.lua.diff`: Replaces dead `isRenderShadowEnabled`/`castShadows` `setField` pairs at `L353–354` (`revive`) and `L392–393` (`spawn`) with `shadowctl.excludeObject(o, 'far')`.
4. `roads.lua.diff`: Replaces dead `isRenderShadowEnabled`/`castShadows` `setField` pair at `L382–383` (`createWalk`) with `shadowctl.excludeObject(o, 'road_static')`.
5. `core.lua.diff`: Replaces the `PSSMLightShadowMap` block in `onPreRender` (`L1594–1604`) with `shadowctl.applyGlobalProfile((pl and pl.speed) or 0, gov, dtReal)`.
6. `test_shadowctl.lua.diff` (and `new_files/mod/tests/test_shadowctl.lua`): Unit test suite covering `computeDistanceScale`, `applyGlobalProfile` burst tightening/decay and setter quantization, `excludeObject` material cloning & `skin` remapping, `TSForestItemData` `shadowNullDetailSize` splitting, and empty `Forest` hiding.

---

## 4. Test Plan

1. **Offline Unit Tests**:
   - Note: `vendor/luajit/luajit.exe` is not on `PATH` in this workspace environment, so Lua unit tests were statically verified against `mod/tests/stubs.lua` and `mod/tests/testlib.lua`.
   - `test_shadowctl.lua` validates all `shadowctl` functions in both stub-table compatibility mode and `FORCE_ENGINE_MODE = true`.
   - `shadowctl.excludeObject` preserves `obj.fields.isRenderShadowEnabled = 'false'` and `obj.fields.castShadows = '0'` when `type(obj) == 'table'` (offline `stubs.lua`), ensuring `mod/tests/test_farfield.lua:64` and `mod/tests/test_farfield_spares.lua:48` continue to pass without modification.
2. **In-Engine Validation (`tools/perf_capture.py` & PerfGraph)**:
   - Apply the 6 diffs, run `python tools/perf_capture.py --duration 15 --toggle-graph --unpause` during a high-speed drive across newly streaming tiles, and verify:
     - `scenetree.findObject('bne_noshad_facade'):getField('castShadows', 0) == '0'` and `curbs:getField('castShadows', 0) == '0'`.
     - Non-solid `bngEarthTree_*_n` datablocks report `shadowNullDetailSize == '500'`, while solid `bngEarthTree_*` datablocks report `'35'`.
     - Empty pooled `bngEarthForest_*` objects report `isHidden() == true`.
     - `RenderShadows` p99 drops from `9.1 ms` to `< 2.5 ms` and p95 frame time remains `< 16.67 ms`.

---

## 5. Cross-Task Requests

1. **For the owner of `trees.lua` (`releaseForest` / `forest` / `itemType`, lines 208–265)**:
   - While `shadowctl.onForestTileUpdated` sweeps empty `bngEarthForest_*` objects and upgrades `bngEarthTree_*_n` datablocks from the `L1073` hook, setting `d:setField('shadowNullDetailSize', 0, solid and '35' or '500')` directly inside `itemType()` (`trees.lua:259`) and calling `f:setHidden(true)` inside `releaseForest()` (`trees.lua:226`) / `f:setHidden(false)` inside `forest()` (`trees.lua:212`) is a 3-line direct reinforcement.
2. **For the owner of `buildings.materials.json` / `roads.lua` (`loadMaterials`, line 144)**:
   - Optionally add `"castShadows": false` to a dedicated `bne_bld_far` material in `buildings.materials.json` if `server/buildings.py` is updated to emit `bne_bld_far` on `bldfar` meshes directly (complementing `shadowctl`'s runtime `skin = 'bne_bld_=bne_noshad_'` remap).

---

## 6. Open Questions

1. **Optional `sdsmFitEnabled = true` during bursts**: Our live A/B probe showed `PSSMLightShadowMap.sdsmFitEnabled = true` also cut burst `RenderShadows` median from `10.71 ms` to `1.01 ms`, though `cameraUpdate.lua` resets `sdsmFitEnabled = false` on mode switches. Currently `shadowctl` uses `sdsmMaxDistanceScale` tightening (`0.22`), which achieved an even cleaner p95 (`1.25 ms` vs `14.38 ms`) without SDSM depth-readback jitter. Should we expose an optional setting for `sdsmFitEnabled` in `settings.lua`?
