# Phase 10 Wave 1 — W4 (`roads` / `farfield` / `materials` / `server/buildings`) Report

## 1. Summary of Changes (`file:line`)

### A. Wave-2 Items Removed (Requirement 1)
- [farfield.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L115-L116): Restored `M.SPARE_MAX = 64` and `M.SPARE_S = 30` (D4 pool shrinkage deferred to Wave 2). Kept immediate `SPARE_MAX` enforcement inside `park(inst)` ([L522-L531](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L522-L531)) and tagged parked entries with `q = sT` ([L523](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L523), [L1576-L1583](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L1576-L1583)) so stale `spareQ` slots from previously revived tiles never evict a newly re-parked copy of the same key.
- [buildings.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L76-L78): Removed `LITE_ALBEDO` vertex-colour baking, removed the `lite` plain-wall UV remap in `_walls` ([L840](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L840)) and `build()` ([L1563-L1579](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L1563-L1579)), and restored `BLD_LOD_PX = 2700.0` ([L2297](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L2297)). Kept `FAR_MAT = "bne_bld_far"`, `build(..., lite=False, far=False)`, and `far_tile()` passing `far=True` ([L2634](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L2634)) so distant `bldfar` tiles use a single shadowless primitive (`("bne_bld_far",)`).

### B. R4 Consistency & Material Definitions (Requirement 2)
- [roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L23): Cached `local shadowctl = require('beamngEarth/shadowctl')` in a module upvalue and called `shadowctl.excludeObject(o, 'road_static')` in `createWalk` ([L434](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L434)).
- [farfield.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L94): Cached `local shadowctl = require('beamngEarth/shadowctl')` in a module upvalue and called `shadowctl.excludeObject(o, 'far')` in `revive` ([L355](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L355)) and `spawn` ([L393](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L393)).
- [satmat.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/satmat.lua#L116): Enforced `m:setField('castShadows', 0, '0')` when adopting an existing runtime `Material` in `M.create`.
- [buildings.materials.json](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json#L453-L481): Verified `bne_bld_far` is defined with `"castShadows": false`, `"vertColor": true`, and the full `t_highrise_plaster` texture set matching `bne_bld_facade`, and `"castShadows": false` is set on `bne_bld_marble` ([L395](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/buildings.materials.json#L395)).
- [tunnel.materials.json](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json#L30): Verified `"castShadows": false` on `bne_tunnel_light` ([L31](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json#L31)) and `bne_tunnel_soil` ([L113](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/levels/beamng_earth/art/shapes/beamngEarth/tunnel.materials.json#L113)).

### C. R6 — Stock Materials Idempotence & Conditional `flush`/`reload` (Requirement 3)
- [roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L153-L188): Documented that stock levels reload their `.materials.json` on level load. Made `loadMaterials()` check `m:getField('castShadows', 0)` (and `translucent` / `baseColorFactor` for `M.OPAQUE` / `tactile_indicator`, coalescing `castShadows = '0'` on those three materials) so `m:flush(); m:reload()` is only invoked when the field value actually changes, and only once per level load (`loadedMaterials = true`).

### D. Reveal Pacing & Scene-Graph Reductions (Requirements 3 & 5)
- [farfield.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L1445): Updated `maxReveals` to `(((gov.burst and not gov.urgent) and 1) or M.REVEALS_PER_FRAME or 2)` so `gov.urgent` overrides `gov.burst` (R1).
- [roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L888-L889): Fixed `colDirty` threshold from strict `>` to `>=` (`timeSinceLastReload >= M.RELOAD_EVERY_S`), eliminating the 1 ms `os.clock()` quantization race when `M.RELOAD_EVERY_S = 0` in tests.

---

## 2. Server `bldfar` Disk Cache Investigation (Requirement 4)

- **Finding**: **There is no persistent disk cache for built `bldfar` meshes.**
- Tracing [buildings.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L2618-L2648) (`far_tile`), [blockworker.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/blockworker.py#L479-L484) (`far_buildings_tile`), [earthd.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/earthd.py#L1031-L1046) (`build_far_bld_tile`), and [vegetation.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/vegetation.py#L887-L932) confirms that `bldfar_<aid>_<tx>_<ty>.cdae` files are generated on-demand from `mapdata` vector layers directly into the ephemeral per-session directory (`temp/beamngEarth/<sessionId>/`) and pooled into `slot_<n>.cdae`. No cache version bump is needed because no pre-built `bldfar` `.cdae` meshes persist across server sessions.

---

## 3. Test Summary (Requirement 5)

- `mod/tests/test_roads.lua`:
  - Fixed `renderOff` check ([L137](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_roads.lua#L137)) to inspect `o.renderEnabled == false` (set by `stubs.lua`'s `o:setRenderEnabled(false)`).
  - Investigated and fixed the flaky `"then the pending rebuild runs"` (and `"dropped tile: mesh deleted, collision reloaded"`) failure caused by `timeSinceLastReload > M.RELOAD_EVERY_S` (`0 > 0`) when Windows `os.clock()` (1 ms resolution) had not ticked between back-to-back `roads.update` calls with `RELOAD_EVERY_S = 0`.
  - Added R6 unit test ([L332-L359](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_roads.lua#L332-L359)) verifying `M.NO_SHADOW` sets `castShadows = '0'`, only calls `flush`/`reload` on materials whose value changed, runs once per level load, and is idempotent across level resets.
  - **Result**: `test_roads: 74 passed, 0 failed`
- `mod/tests/test_farfield_spares.lua`:
  - Restored default check to `SPARE_MAX == 64 and SPARE_S == 30` ([L28](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_farfield_spares.lua#L28)) and re-sent expired child tiles before testing immediate `SPARE_MAX = 2` eviction in `park()` ([L69-L77](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_farfield_spares.lua#L69-L77)).
  - **Result**: `test_farfield_spares: 26 passed, 0 failed`
- `mod/tests/test_farfield.lua`:
  - Extended P10-B reveal cap test ([L870-L926](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_farfield.lua#L870-L926)) to cover `REVEALS_PER_FRAME = 2` in normal governed mode, `1` in burst mode (`gov.burst and not gov.urgent`), and `2` when `gov.urgent` overrides `gov.burst`.
  - **Result**: `test_farfield: 178 passed, 2 failed` (only the 2 pre-existing baseline failures in `scratch/p10w1_baseline_lua_failures.txt`).
- `server/tests/test_buildings.py`:
  - Updated `SplitTest.test_shadow_materials_and_lite_window_omission` ([L378-L410](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/tests/test_buildings.py#L378-L410)) to remove Wave-2 UV remap assertions and verify `far=True` returns `("bne_bld_far",)`, encodes `["bne_bld_far"]` into `.cdae`, and keeps `BLD_LOD_PX == 2700.0`.
  - **Result**: `Ran 56 tests in 0.266s — OK`

---

## 4. Risks & Cross-Task Requests

- **Risks**: Low. Removing the Wave-2 `lite` UV remap/vertex-colour baking leaves `bldfar` and near `detail2` visual appearance identical to baseline while `bne_bld_far` (`castShadows: false`) eliminates shadow draw submissions for all `bldfar` horizon tiles.
- **Cross-Task Requests**:
  - `server/prewarm.py` (not owned by W4): Consider adding `buildings.FAR_MAT` (`"bne_bld_far"`) to `prewarm.materials()` (`server/prewarm.py:40`) so `bne_bld_far` is prewarmed at level start alongside `buildings.MATERIALS`.

STATUS_UPDATE: DONE (100%)
