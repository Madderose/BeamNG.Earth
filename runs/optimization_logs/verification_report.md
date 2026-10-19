## Verification Sign-Off Report

**Status:** **APPROVED WITH 1 FIX APPLIED**  
**Test Suite (`test_roads.py`, `test_furniture.py`, `test_buildings.py`):** `Ran 91 tests in 6.083s — OK`  
**Extended Suites (`test_fast.py`, `test_roadmesh.py`, `test_vegetation.py`, `test_grading.py`):** `Ran 53 tests in 7.628s — OK`

---

### 1. Audit Summary by Task

#### TASK-01: Streaming & Road Priority
* **[roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L345-L347)**:
  * Verified `table.insert(walkQ, 1, { key = key, walk = road, what = 'road' })` inserts road surface collision/render meshes at the front of `walkQ` (which pops via `table.remove(walkQ, 1)` in [`M.tick`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L590)), ensuring drivable surfaces instantiate before secondary tile assets while respecting the `SPAWN_BUDGET_S` frame budget.
* **[roadmesh.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roadmesh.py#L97-L133)**:
  * Verified [`drape_mesh`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roadmesh.py#L61-L162) batches left edge, right edge, and centreline (`0.5 * (l + r)`) into a single `elev` call (`k0` advances by `3 * k` for ribbons and `k` for `polys`), and applies `slope_lift = np.clip(0.12 * cross_dz, 0.0, 0.18)` to prevent terrain pokethrough on crowned/cross-sloped ground.
* **[roads.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roads.py#L1940-L1978)** & **[earthd.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/earthd.py#L2626)**:
  * Verified [`Tracker.on_pose`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roads.py#L1940-L1978) computes velocity-aware lookahead (`lead = min(384.0, speed * 8.0)` when `speed > 5.0`), cosine-weighted directional priority `_prio`, and retains tiles in `want_set` without premature eviction.
* **Determinism Bug Fixed in [`build_tile`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roads.py#L1768-L1775)**:
  * **Issue:** TASK-01 had clipped `ring` coordinates to `cbox = (near[0] - 16.0, near[1] - 16.0, near[2] + 16.0, near[3] + 16.0)` before constructing `roads`. Because [`furniture.place`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/furniture.py#L368-L553), [`_stations`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/furniture.py#L314-L327), and [`speed_signs`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/furniture.py#L569-L639) compute arc-length stations from `line[0]`, clipping `ring` to tile-dependent `cbox` boundaries shifted `line[0]` per tile—violating deterministic generation across tile boundaries, breaking wire spans across tile borders, potentially creating duplicate `fid` entries on curved roads, and breaking closed loops in [`islands.find`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/islands.py#L96-L157).
  * **Fix:** Replaced destructive `cbox` geometry clipping in [`build_tile`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roads.py#L1768-L1775) with a non-destructive `cbox` intersection filter using [`clip_polyline`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roads.py#L905-L947), preserving full unclipped road geometry for downstream stationing while still skipping diagonal false-positive roads outside `cbox`.

#### TASK-02: Object Heights & Vegetation Grader Integration
* **[furniture.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/furniture.py#L267-L274)**:
  * Verified [`_sample_z`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/furniture.py#L267-L274) guards against exceptions and non-finite DEM samples with a finite fallback.
  * Verified town utility poles (`G_POLE`), cobra-head streetlamps (`G_POLELAMP`), and catenary wire endpoints in [`place`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/furniture.py#L439-L448) and [`_emit_post`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/furniture.py#L496-L505) add `curb_h` (`0.15 m` in town), aligning pole bases and wire spans with the raised sidewalk surface.
* **[earthd.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/earthd.py#L846-L852)**:
  * Verified [`build_veg_tile`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/earthd.py#L832-L865) queries `g = self.grader_for(anchor)` and applies `g.apply(la, lo, z, gradingmod.ROAD_LIFT)` in `veg_elev`, ensuring roadside trees and bushes sit on graded embankments/cuts rather than floating or burying.

#### TASK-03: Building Scale, Height & Footprint Fixes
* **[buildings.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py)** & **[test_buildings.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/tests/test_buildings.py)**:
  * Verified storey distribution adjustments in [`classify`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L450-L465) and tighter pitched-roof gates (`box_fill < 0.90`, `hw > 8.5` for houses) in [`classify`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L495-L515) prevent L-shaped and wide footprints from inflating into oversized oriented bounding boxes.
  * Verified roof ridge rise cap (`6.5 m` for churches, `4.2 m` otherwise) and eave drop `ze = z_eave - EAVE_M * (rise / hw2)` in [`_pitched_box`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L984-L989) cannot divide by zero (`hw >= 2.0`, `EAVE_M = 0.35`).
  * Verified [`build_parts`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L1029-L1055) eliminates duplicate `_build_one` invocations while respecting `MAX_MESH_VERTS = 60000`.
  * Verified hillside anchoring (`g_base = min(gmax, gmin + 1.5)`) in [`_build_one`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L1213-L1275) and [`building_props`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L1715-L1760) keeps doors, stoops, porches, and eaves aligned with the ground while maintaining the foundation skirt down to `gmin - FOUNDATION_M`.

#### TASK-04: Native Kernels & Fast Fallbacks
* **[lib.rs](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/native/earthfast/src/lib.rs)**:
  * Verified all 16 compute-intensive PyO3 functions copy views into owned Rust slices/Vecs before entering `py.allow_threads(|| ...)` and construct NumPy arrays after re-acquiring the GIL, with explicit zero-length, degenerate-segment, and `NaN` guards.
* **[fast.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/fast.py)**:
  * Verified all 19 pure-NumPy fallback kernels match the native `earthfast` signatures, dtypes, and edge-case semantics when `_ef is None`.

---

### 2. Golden Principles Checklist ([docs/ROADMAP.md](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/docs/ROADMAP.md))
* **Deterministic Generation:** Preserved across tiles and rebases (after fixing `cbox` clipping in [`roads.py`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roads.py#L1768-L1775)); verified by `test_tile_determinism` and `test_rebase_determinism`.
* **Mesh Complexity Limits (`< 8192` tris / `< 65535` verts):** Preserved via `MAX_VERTS = 60000` in [`roadmesh.py`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roadmesh.py#L22) and `MAX_MESH_VERTS = 60000` in [`buildings.py`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py#L1026).
* **Frame Safety (`< 2 ms` Lua tick budget):** Preserved in [`roads.lua`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L19) (`SPAWN_BUDGET_S = 0.002`) and GIL-free Rust kernels in [`lib.rs`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/native/earthfast/src/lib.rs).
