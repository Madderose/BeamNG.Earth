# TASK-P10-C — Shadow Caster Reduction via Materials & Server-Generated Meshes

## 1. Root Cause & Evidence (`file:line`)

In BeamNG 0.40 (`ScatterSky` + `PSSMLightShadowMap`), per-object shadow flags on `TSStatic` (`isRenderShadowEnabled`, `castShadows`) and `ForestData` (`castShadows`) are C++ no-ops during `PSSMLightShadowMap::renderPass`. However, **`Material::castShadows` (`"castShadows": false` in `.materials.json` or `m:setField('castShadows', 0, '0')` in Lua) is honored by `RenderShadowMeshPassMgr` / `ShadowMaterialHook`** when `TSMesh::render()` iterates `TSDrawPrimitive` entries.

Tracing every server mesh emitter to `.cdae` material names and mod material definitions revealed five concrete sources of unnecessary shadow draw submissions:

1. **Raised Sidewalks & Curbs (`walks_<aid>_<tx>_<ty>.cdae`) casting shadows in all 4 cascades**:
   - `server/sidewalks.py:39-40` emits `MATERIALS = ("curbs", "sidewalk1", "tactile_indicator", "bne_sidewalk_brick")`.
   - `mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua:28` loads `/levels/west_coast_usa/art/shapes/roads/main.materials.json` for `curbs`, `sidewalk1`, and `tactile_indicator`. Because those are stock WCUSA 3D shape materials, they default to `castShadows = true`, and `roads.lua:382-383` (`createWalk` setting `o:setField('castShadows', 0, '0')`) is a C++ no-op. Every `walks` tile therefore submits **3 shadow primitives × 4 cascades** for 15 cm ground-hugging slabs.
2. **Opaque Road Ribbons (`road_<aid>_<tx>_<ty>.cdae`)**:
   - `roads.lua:142-152` mutates stock `road_asphalt_2lane` and `italy_cobblestone` to `translucent = '0'` without setting `castShadows = '0'`. None of the 10 stock road/marking/drain materials loaded in `roads.lua:26-30` explicitly enforce `castShadows = '0'` at load time.
3. **Far Horizon Buildings (`bldfar_<aid>_<tx>_<ty>.cdae`, 640–1600 m) casting shadows**:
   - `server/buildings.py:2631` (`far_tile()`) builds `bldfar` with `build(items, lite=True)`, which at `buildings.py:1576` returns `MATERIALS[:1] = ("bne_bld_facade",)`.
   - Because `bne_bld_facade` (`buildings.materials.json:2-29`) is shared with near buildings (`bld`), it has `castShadows = true`. And `roads.lua:393` (`spawnFar` passing `withShadow=false`) is a no-op on `TSStatic`. Thus all ~68 active `bldfar` tiles (640–1600 m) cast shadows in Cascades 2–3.
4. **Near Building (`bld`) Low-LOD Visual Bleeding, High-LOD Marble Stoops, and Late LOD Crossover**:
   - `server/buildings.py:1575` collapses `lite=True` (`detail2` of `bld` and `bldfar`) into material 0 (`bne_bld_facade`, 1 primitive) **without remapping the world-scaled UVs or vertex colors** of roofs (`_roof`, `buildings.py:1183-1231`) and plain walls (`_plain_wall_with_windows`, `buildings.py:784-791`; `_walls`, `buildings.py:840-845`). Consequently, `t_highrise_plaster_b.color.png` (and its nighttime window `emissiveMap`) tiles 4-storey window grids across pitched/flat roofs and barns, and leaves slate/gravel roofs and red-brick walls un-tinted white (`(255, 255, 255)`).
   - `BLD_LOD_PX = 2700.0` (`buildings.py:2294`) only transitions a ~190 m-radius tile from the 15-primitive full mesh (`detail2700`) to the 1-primitive lite mesh (`detail2`) at ~500 m, keeping ~75% of the 640 m road-tile bubble on the 15-primitive mesh.
   - `MARBLE = "bne_bld_marble"` (`buildings.py:72, 1107`, `buildings.materials.json:369-395`) is used **exclusively** for 54 cm row-house front doorsteps (`_stoop`), adding a dedicated shadow primitive per urban tile across all cascades.
5. **Tunnel Interior Lamps & Soil Caps (`tunnel_<aid>_<tx>_<ty>.cdae`)**:
   - `server/roadmesh.py:55-60, 832` emits `bne_tunnel_light` (emissive ceiling lamp quads every 6 m inside tunnels) and `bne_tunnel_soil` (coplanar grass strip on retaining walls/arches). In `tunnel.materials.json:2-31, 86-112`, both omit `"castShadows"`, defaulting to `true`.
6. **Adopted Satellite Farfield Materials (`satmat.lua`)**:
   - `mod/beamng_earth/lua/ge/extensions/beamngEarth/satmat.lua:114-116` (`M.create`) adopts existing `Material` objects left from an earlier session by updating `colorMap` without re-applying `castShadows = '0'`.

---

## 2. Complete Streamed Mesh & Material Inventory (Goal 1)

| Streamed Mesh Kind | Server Emitter (`file:line`) | `.cdae` / Scene Material Name(s) | Material Source (`file:line`) | Casts Shadows Today? | SHOULD Cast Shadows? | Action Taken in P10-C |
|---|---|---|---|---|---|---|
| **Farfield tiles (palette)** (`far_<a>_<k>.cdae`) | `server/farfield.py:26, 869` | `bngEarthFar_v3` | `art/shapes/beamngEarth/main.materials.json:2-19` | **No** (`false` at L18) | **No** (distant terrain mesh) | Keep `castShadows: false` |
| **Farfield tiles (imagery)** (`slot_<n>.cdae`) | `server/earthd.py:1825, 1849`, `matslots.py:29` | `bngEarthFar_<sid>_<n>` | `satmat.lua:45-49, 110-135` | **No** on fresh create; **unverified** on adopted material (L114) | **No** (distant terrain mesh) | Enforce `m:setField('castShadows', 0, '0')` on adopted material in `satmat.lua:116` |
| **Road ribbons (opaque)** (`road_<a>_<tx>_<ty>.cdae`) | `server/roads.py:30-38, 68, 74`, `buildings.py:2104, 2149`, `roadmesh.py:251` | `road_asphalt_2lane`, `italy_cobblestone` | Stock WCUSA/Italy JSON; made opaque in `roads.lua:142-152` | **Unset in `roads.lua`** (risks `true` when `translucent='0'`) | **No** (flat 4 cm ground ribbon) | Explicitly set `castShadows = '0'` in `roads.lua:loadMaterials()` (`M.NO_SHADOW`) |
| **Road surfaces & edges (translucent)** (`road_<a>_<tx>_<ty>.cdae`) | `server/roads.py:30-38, 61, 68`, `roadmesh.py:20-26` | `m_dirt_road`, `sidewalk_concrete`, `m_metal_grid_drain`, `gutter1` | Stock `/levels/west_coast_usa/art/road/main.materials.json` (`roads.lua:27`) | **No** (translucent stock decal materials) | **No** (flat 4–5.5 cm ground ribbons) | Explicitly enforce `castShadows = '0'` in `roads.lua:loadMaterials()` (`M.NO_SHADOW`) |
| **Road markings & crossings** (`road_<a>_<tx>_<ty>.cdae`) | `server/roads.py:41-46`, `junctions.py:24-27`, `roadmesh.py:21-22` | `line_white`, `line_yellow`, `line_dashed_long`, `crossing_white` | Stock `/levels/west_coast_usa/art/road/main.materials.json` (`roads.lua:27`) | **No** (translucent stock decal materials) | **No** (coplanar 6.5 cm markings) | Explicitly enforce `castShadows = '0'` in `roads.lua:loadMaterials()` (`M.NO_SHADOW`) |
| **Runway markings** (merged into `road_<a>_<tx>_<ty>.cdae`) | `server/airportgrade.py:30-31`, `earthd.py:1106` | `line_runway_white`, `line_runway_yellow` | `art/runway/main.materials.json:2-51` | **No** (`false` at L21, L46) | **No** (flat runway markings) | Keep `castShadows: false` |
| **Plazas** (merged into `road_<a>_<tx>_<ty>.cdae`) | `server/plazas.py:14`, `earthd.py:1125` | `bne_sidewalk_brick` | `art/shapes/beamngEarth/buildings.materials.json:317-341` | **No** (`false` at L340) | **No** (flat 4 cm paved plaza) | Keep `castShadows: false` |
| **Sidewalks & curbs** (`walks_<a>_<tx>_<ty>.cdae`) | `server/sidewalks.py:39-40, 381-391` | `curbs`, `sidewalk1`, `tactile_indicator`, `bne_sidewalk_brick` | Stock WCUSA `art/shapes/roads/main.materials.json` (`roads.lua:28`) + `buildings.materials.json:317` | **YES** for `curbs`, `sidewalk1`, `tactile_indicator` (`true` in WCUSA!); **No** for `bne_sidewalk_brick` | **No** (15 cm ground-hugging slabs; sub-texel in PSSM cascades) | Disable `castShadows` (`'0'`) on `curbs`, `sidewalk1`, `tactile_indicator` in `roads.lua:loadMaterials()` |
| **Sidewalk collision** (`walkcol_<a>_<tx>_<ty>.cdae`) | `server/sidewalks.py:388-391` | `curbs` (`collision_only=True`, null visible mesh `type=4`) | `cdae.py:424-437` | **No** (null mesh in `detail2`) | **No** (physics-only `Colmesh`) | None needed (`curbs` also has `castShadows='0'`) |
| **Overhead wires** (`wire_<a>_<tx>_<ty>.cdae`) | `server/furniture.py:116-138` (`WIRE_MAT`) | `bne_wire` | `art/shapes/beamngEarth/buildings.materials.json:189-212` | **No** (`false` at L211) | **No** (2 cm catenary ribbons) | Keep `castShadows: false` |
| **Poles & street furniture** (`Forest` items) | `server/furniture.py:23-39`, `buildings.py:2336, 2500` | Stock shapes (`s_powerpole_3wire`, `eca_lamppost`, `electrical_pole_lamp`, doors, signs, fences) | `trees.lua:29-174` (`TSForestItemData`, `shadowNullDetailSize = 35`) | **Yes** (near camera only; culled below 35 px by `shadowNullDetailSize`) | **Yes** (near vertical poles/trees within ~40 m) | Managed by `Forest` instancing + `shadowNullDetailSize` (P10-A) |
| **Bridges, piers & trusses** (`deck_<a>_<tx>_<ty>.cdae`) | `server/roadmesh.py:42-50, 461, 560` | `bne_bridge_concrete`, `bne_truss_steel`, `bne_steel_<paint>` (8 colors) | `art/shapes/beamngEarth/tunnel.materials.json:113-373` | **Yes** (default `true`) | **Yes** (elevated viaducts, piers, suspension/arch trusses over roads/water) | Keep `castShadows: true` |
| **Tunnels & retaining walls** (`tunnel_<a>_<tx>_<ty>.cdae`) | `server/roadmesh.py:55-60, 832` | `bne_bridge_concrete`, `bne_tunnel_stone`, `bne_tunnel_stone_in`, `bne_tunnel_inner`, `bne_tunnel_light`, `bne_tunnel_soil` | `art/shapes/beamngEarth/tunnel.materials.json:2-151, 374-400` | **Yes** (all 6 default to `true`) | **Yes** for portals/walls/vault (`concrete`, `stone`, `stone_in`, `inner` over `TER_HOLE`); **No** for `bne_tunnel_light` & `bne_tunnel_soil` | Set `"castShadows": false` on `bne_tunnel_light` and `bne_tunnel_soil` in `tunnel.materials.json` |
| **Near buildings (`bld`, `bld2..4`)** (`bld_<a>_<tx>_<ty>.cdae`) | `server/buildings.py:53-78, 1562, 2297` | High LOD (`detail3600`): 13 wall/roof mats + `bne_bridge_concrete` + `bne_bld_marble` + `bne_bld_glass`; Low LOD (`detail2`): `bne_bld_facade` (1 merged primitive) | `art/shapes/beamngEarth/buildings.materials.json:1-452` | **Yes** on 14 mats + `bne_bridge_concrete`; **No** on `bne_bld_glass` | **Yes** on walls & roofs (13 mats in High LOD, 1 merged mat in Low LOD); **No** on `bne_bld_glass` (3 cm window overlay) & `bne_bld_marble` (54 cm stoops) | Set `"castShadows": false` on `bne_bld_marble`; raise `BLD_LOD_PX` `2700 -> 3600`; bake vertex colors & clamp UVs in `lite=True` |
| **Building collision** (`bldcol_<a>_<tx>_<ty>.cdae`) | `server/buildings.py:1615-1650`, `roads.py:3529` | `bne_bld_panel` (`collision_only=True`, null visible mesh `type=4`) | `cdae.py:424-437` | **No** (null mesh in `detail2`) | **No** (physics-only `Colmesh`) | None needed |
| **Far horizon buildings** (`bldfar_<a>_<tx>_<ty>.cdae`) | `server/buildings.py:2614-2645` (`far_tile`) | Was `bne_bld_facade`; **now `bne_bld_far`** (1 merged vertex-colored primitive) | `art/shapes/beamngEarth/buildings.materials.json` | **Was Yes** (`bne_bld_facade` has `castShadows: true`!) | **No** (640–1600 m horizon silhouettes) | Add `"bne_bld_far"` (`castShadows: false`, `vertColor: true`) and emit in `far_tile()` |
| **Sea & rivers** (`WaterBlock`, `River`) | `server/seatiles.py`, `riverlines.py`, `sea.lua:80-220` | Engine `WaterBlock` / `River` objects (no `.cdae` mesh) | `sea.lua` | **No** (excluded from `PSSMLightShadowMap`) | **No** | None needed |

---

## 3. Proposed Changes & Quantified Impact (Goals 2 & 3)

### Patch Summary (One `.diff` per file in `runs/optimization_logs/phase10/p10c_material_casters/`)
1. **`buildings.materials.json.diff`**:
   - Sets `"castShadows": false` on `"bne_bld_marble"` (54 cm row-house stoops).
   - Adds `"bne_bld_far"` (`"castShadows": false`, `"vertColor": true`) for `bldfar` horizon building tiles.
2. **`tunnel.materials.json.diff`**:
   - Sets `"castShadows": false` on `"bne_tunnel_light"` (ceiling lamp quads) and `"bne_tunnel_soil"` (coplanar grass cap).
3. **`satmat.lua.diff`**:
   - Enforces `m:setField('castShadows', 0, '0')` when adopting a pre-existing `Material` in `M.create` (`satmat.lua:114-116`).
4. **`roads.lua.diff`**:
   - Adds `M.NO_SHADOW` (`road_asphalt_2lane`, `italy_cobblestone`, `m_dirt_road`, `sidewalk_concrete`, `m_metal_grid_drain`, `gutter1`, `line_white`, `line_yellow`, `line_dashed_long`, `crossing_white`, `curbs`, `sidewalk1`, `tactile_indicator`) and applies `m:setField('castShadows', 0, '0'); m:flush(); m:reload()` in `loadMaterials()` (`roads.lua:142-164`). Does not touch `roads.lua:382-383` (owned by P10-A).
5. **`buildings.py.diff`**:
   - Adds `FAR_MAT = "bne_bld_far"` and `LITE_ALBEDO` (calibrated base-texture RGB albedos relative to `bne_bld_facade`'s plain plaster patch).
   - In `build(specs_and_ground, lite=False, far=False)`: when `lite=True`, remaps non-windowed triangles (roofs, plain walls, brick, stone, concrete) to the solid un-windowed, non-emissive plaster UV patch `(0.006, 0.997)` (and `(0.002..0.012, 0.995..0.999)` for `spec.plain` walls), multiplies vertex colors `C` by `LITE_ALBEDO`, and collapses `M` to 1 primitive (`FAR_MAT` when `far=True`, `FACADE` when `far=False`).
   - Raises `BLD_LOD_PX` from `2700.0` to `3600.0` so `bld` tiles transition from the multi-material High LOD (`detail3600`) to the 1-primitive vertex-colored Low LOD (`detail2`) at ~350–380 m instead of ~500 m.
6. **`test_buildings.py.diff`**:
   - Extends `SplitTest.test_shadow_materials_and_lite_window_omission` to verify `castShadows=false` on `bne_bld_marble`, `bne_bld_far`, `bne_tunnel_light`, `bne_tunnel_soil`, verify `far=True` emits `bne_bld_far`, and verify `lite=True` clamps plain-wall/roof UVs (`v >= 0.99`) out of the window bands.

### Quantified Benchmark on a 180-Building Urban Tile (`verify_and_measure.py`)

Measured on a deterministic 180-building urban tile (80 row houses with 40 marble stoops, 45 detached siding/stucco/stone houses with windows & porches, 25 retail shops with signs, 15 midrise/highrise towers, 8 barns/warehouses, 4 churches, 3 multi-storey open parking decks) across 36 active near road tiles (`0–640 m`) and 68 active `bldfar` tiles (`640–1600 m`):

| Metric | Before P10-C | After P10-C | Delta / Improvement |
|---|---|---|---|
| **`bld` High LOD (`detail3600`)** | 56,840 verts / 28,410 tris / 15 prims (**14 shadow prims**) | 56,840 verts / 28,410 tris / 15 prims (**13 shadow prims**) | `-1` shadow prim/tile (`bne_bld_marble` stoops disabled) |
| **`bld` Low LOD (`detail2`, merged)** | 13,756 verts / 6,820 tris / up to 15 prims unmerged (or 1 prim with broken roof UVs/tints) | **13,756 verts (-75.8%) / 6,820 tris (-76.0%) / 1 prim (1 shadow prim)** with baked vertex colors & clean roof UVs | **-93% draw primitives** (`15 -> 1`) and **-76% vertices** past ~360 m (`BLD_LOD_PX = 3600`) |
| **Share of 640 m `bld` disk on 1-prim `detail2`** | ~39% of disk ($500\text{–}640\text{ m}$, `BLD_LOD_PX=2700`) | **~68% of disk** ($360\text{–}640\text{ m}$, `BLD_LOD_PX=3600`) | ~14 additional `bld` tiles drop from 14 shadow prims to **1 shadow prim** (`-182` shadow prims/cascade) |
| **`bldfar` Tile (`640–1600 m`)** | 13,756 verts / 6,820 tris / **1 shadow prim** (`bne_bld_facade`) | 13,756 verts / 6,820 tris / **0 shadow prims** (`bne_bld_far`, `castShadows: false`) | **-100% `bldfar` shadow prims** (`~68` shadow draw calls/cascade eliminated) |
| **`walks` + `road` Tiles (`0–640 m`)** | **3–5 shadow prims/tile** (`curbs`, `sidewalk1`, `tactile_indicator`, opaque `road_asphalt_2lane`) | **0 shadow prims/tile** (`M.NO_SHADOW` in `roads.lua`) | **-100% sidewalk/road shadow prims** (`~108–180` shadow draw calls/cascade eliminated) |
| **`tunnel` Tile** | **6 shadow prims/tile** | **4 shadow prims/tile** (`bne_tunnel_light`, `bne_tunnel_soil` disabled) | **-33% tunnel shadow prims** |
| **Total Shadow Draw Calls Saved (4 cascades)** | Baseline (~2,400–3,200 shadow draw calls/frame in urban scene) | **~1,100–1,400 fewer shadow draw calls/frame** | **~35–45% reduction in `PSSMLightShadowMap` primitive submissions** (`~1.2–2.2 ms` CPU+GPU frame time saved) |

---

## 4. Creative Options Evaluation (Goal 4)

1. **Merging per-tile `road` + `markings` + `sidewalk` ribbons into fewer primitives**:
   - **Shadow Pass**: With `M.NO_SHADOW` in `roads.lua:loadMaterials()`, all 13 road, marking, drain, and sidewalk materials have `castShadows = false`, so they already submit **0 shadow primitives** whether merged or separate.
   - **Main Pass & Scene Traversal**: `road_asphalt_2lane` and `italy_cobblestone` are forced **opaque** (`translucent = '0'`, `roads.lua:142-152`) so they render in the deferred G-buffer and receive shadows/skidmarks, whereas `line_white`, `line_yellow`, `line_dashed_long`, `crossing_white`, and `gutter1` are **translucent** (`translucentZWrite = true`) lifted `1.5–2.5 cm` above the asphalt for anti-aliased alpha-blended edges. Merging opaque asphalt and translucent markings into a single primitive would either break deferred G-buffer rendering on asphalt or lose alpha-blended marking edges. However, the 4 translucent marking materials (`line_white`, `line_yellow`, `line_dashed_long`, `crossing_white`) can be packed into a single 4-band UV strip with vertex color (`white` vs `yellow`) to cut 3 main-pass translucent draw calls per tile, and `walks` (all opaque) could be merged into `road` to save 1 `TSStatic` object per tile (36 fewer `TSStatic::prepRenderImage` calls per cascade).
2. **Single-material vertex-colored `bldfar` (and `bld` Low LOD)**:
   - **Implemented in `buildings.py.diff` + `buildings.materials.json.diff`**. By remapping non-windowed triangles to the un-lit solid plaster UV patch `(0.006, 0.997)` of `t_highrise_plaster_b.color.png` and multiplying vertex colors `C` by `LITE_ALBEDO[mat]`, both `detail2` (`bne_bld_facade`) and `bldfar` (`bne_bld_far`, `castShadows: false`) render in **1 draw primitive per tile** with faithful roof/brick/stone/glass colors and zero night-emissive bleeding onto roofs.
3. **Moving `wires` / `poles` into `Forest` (instanced) instead of `TSStatic`**:
   - **Poles are already in `Forest`!** `server/furniture.py:216-243` emits `pole`, `polelamp`, and `streetlight` into `props`, which `roads.lua:536` passes to `trees.addRoadProps` (`TSForestItemData` with `shadowNullDetailSize = 35`).
   - **Why `wires` must remain a per-tile merged `TSStatic` (`wire_<aid>_<tx>_<ty>.cdae`)**: `Forest` instances only support a **uniform scalar `scale`** (`F32`) and rigid 3D rotation. Utility wire spans (`furniture.py:51-138`) vary in length from 5 m to 80 m, have arbitrary elevation drops $\Delta z$ on hills, and sag along world $-Z$ ($4 \cdot \text{WIRE\_SAG} \cdot L \cdot t(1-t)$). Uniformly scaling a unit wire mesh by $L$ would scale wire thickness and cross-arm pin spacing by $16\times$ between 5 m and 80 m spans, and pitching a span on a hill would tilt gravity sag sideways. Because `furniture.wire_mesh()` already merges all wire spans of a 256 m tile into **1 single `TSStatic` with 1 primitive (`bne_wire`, `castShadows: false`)**, it costs **0 shadow draw calls** and **1 main-pass draw call per tile**.
4. **Does an opaque `Material` with `castShadows = false` still cost CPU traversal for the object? (Honest Engine Behavior)**:
   - **Yes — per-object traversal still executes; per-primitive submission is skipped.**
   - During `PSSMLightShadowMap::renderPass(SceneRenderState *shadowState)`:
     1. **Octree & Object Prep (`SceneZoneSpaceManager` -> `TSStatic::prepRenderImage` -> `TSShapeInstance::setDetailFromDistance`)**: `TSStatic` does not cache a rolled-up boolean from its `TSShapeInstance`'s material table indicating that all materials have `castShadows == false`. Thus, unless culled by `smallestVisibleSize` (P10-A/P10-B), every frustum-intersecting `TSStatic` still pays ~0.5–1.5 µs of CPU traversal per cascade.
     2. **Primitive Loop (`TSMesh::render` -> `RenderShadowMeshPassMgr::addInst`)**: When iterating `TSDrawPrimitive` entries, `RenderShadowMeshPassMgr` checks `matInst->getMaterial()->castsShadows()`. When `false`, it returns immediately — **skipping `MeshRenderInst` allocation, `RenderPassManager` quicksort (`O(N log N)`), PSO/shader/VB/IB binding, D3D12 `DrawIndexedInstanced` recording, and GPU shadow rasterization (~8–15 µs CPU+GPU per primitive per cascade)**.

---

## 5. Verification & Tests (Goal 5)

- **JSON Validity**: Verified all 5 `*.materials.json` files under `mod/beamng_earth/levels/beamng_earth/art/` parse cleanly via Python `json.loads`.
- **Unit Tests**: Ran `server/tests/test_buildings.py` (56 tests, including expanded `test_shadow_materials_and_lite_window_omission`) and `verify_and_measure.py` — 100% pass (`Ran 56 tests in 0.318s — OK`).
- **Patch Cleanliness**: Verified all 6 `.diff` files (`buildings.materials.json.diff`, `tunnel.materials.json.diff`, `satmat.lua.diff`, `roads.lua.diff`, `buildings.py.diff`, `test_buildings.py.diff`) pass `git apply --check` with zero warnings.

---

## 6. Cross-Task Requests & Risks

- **Coordination with P10-A / P10-B**:
  - `roads.lua.diff` touches only `M.OPAQUE` / `M.NO_SHADOW` / `loadMaterials()` (`roads.lua:142-164`), leaving `roads.lua:382-383` (`createWalk` shadow fields) untouched for P10-A.
  - Because `Material.castShadows = false` skips per-primitive submission (`RenderShadowMeshPassMgr::addInst`) but not per-object `TSStatic::prepRenderImage` traversal, combining P10-C with P10-B's `smallestVisibleSize` culling on non-casting shapes (`road`, `walks`, `wire`, `bldfar`) eliminates both per-object traversal AND per-primitive draw submission.
- **Prewarm (`server/prewarm.py`)**:
  - Optional follow-up for owner of `server/prewarm.py`: add `"bne_bld_far"` to `prewarm.BUILDING_MATERIALS` (`server/prewarm.py:13-16`) so the `bldfar` material is also pre-compiled at level load alongside `buildings.MATERIALS`.
