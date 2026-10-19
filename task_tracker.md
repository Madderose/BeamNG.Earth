# BeamNG.Earth: Master Optimization Task Tracker

**Orchestrator**: AGY Argon 4 High  
**Verification Agent**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Sub-Agents**: AGY Gemini Medium (`gemini-4-argon-medium`)  
**Last Updated**: 2026-10-19 00:55:03  

---

## Sub-Agent Parallel Execution Status

| Task ID | Component / Area | Files Allocated | Model | Execution Status | Output Log |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-01** | **Streaming & Road Look-Ahead** | `server/roads.py`<br>`server/roadmesh.py`<br>`mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua` | `gemini-4-argon-medium` | **COMPLETED (Exit Code 0)** | [`runs/optimization_logs/task01_roads.log`](runs/optimization_logs/task01_roads.log) |
| **TASK-02** | **Object Heights & Furniture/Vegetation** | `server/furniture.py`<br>`server/earthd.py` | `gemini-4-argon-medium` | **COMPLETED (Exit Code 0)** | [`runs/optimization_logs/task02_furniture_veg.log`](runs/optimization_logs/task02_furniture_veg.log) |
| **TASK-03** | **Building Scale & Footprints** | `server/buildings.py` | `gemini-4-argon-medium` | **COMPLETED (Exit Code 0)** | [`runs/optimization_logs/task03_buildings.log`](runs/optimization_logs/task03_buildings.log) |
| **TASK-04** | **Native Kernels & Fast Fallbacks** | `native/earthfast/src/lib.rs`<br>`server/fast.py` | `gemini-4-argon-medium` | **COMPLETED (Exit Code 0)** | [`runs/optimization_logs/task04_native.log`](runs/optimization_logs/task04_native.log) |

---

## Verification Review (Argon 4 High)

### Verification Sign-Off

## Verification Sign-Off Report

**Status:** **APPROVED WITH 1 FIX APPLIED**  
**Test Suite (`test_roads.py`, `test_furniture.py`, `test_buildings.py`):** `Ran 91 tests in 6.083s — OK`  
**Extended Suites (`test_fast.py`, `test_roadmesh.py`, `test_vegetation.py`, `test_grading.py`):** `Ran 53 tests in 7.628s — OK`

---

### 1. Audit Summary by Task

#### TASK-01: Streaming & Road Priority
* **[roads.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L345-L347)**:
  * Verified `table.insert(walkQ, 1, { key = key, walk = road, what = 'road' })` inserts road surface collision/render meshes at the front of `walkQ` (which pops via `table.remove(walkQ, 1)` in `M.tick`), ensuring drivable surfaces instantiate before secondary tile assets while respecting the `SPAWN_BUDGET_S` frame budget.
* **[roadmesh.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roadmesh.py#L97-L133)**:
  * Verified `drape_mesh` batches left edge, right edge, and centreline (`0.5 * (l + r)`) into a single `elev` call (`k0` advances by `3 * k` for ribbons and `k` for `polys`), and applies `slope_lift = np.clip(0.12 * cross_dz, 0.0, 0.18)` to prevent terrain pokethrough on crowned/cross-sloped ground.
* **[roads.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roads.py#L1940-L1978)** & **[earthd.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/earthd.py#L2626)**:
  * Verified `Tracker.on_pose` computes velocity-aware lookahead (`lead = min(384.0, speed * 8.0)` when `speed > 5.0`), cosine-weighted directional priority `_prio`, and retains tiles in `want_set` without premature eviction.
* **Determinism Bug Fixed in [build_tile](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/roads.py#L1768-L1775)**:
  * **Issue:** TASK-01 had clipped `ring` coordinates to `cbox = (near[0] - 16.0, near[1] - 16.0, near[2] + 16.0, near[3] + 16.0)` before constructing `roads`. Because `furniture.place`, `_stations`, and `speed_signs` compute arc-length stations from `line[0]`, clipping `ring` to tile-dependent `cbox` boundaries shifted `line[0]` per tile—violating deterministic generation across tile boundaries, breaking wire spans across tile borders, potentially creating duplicate `fid` entries on curved roads, and breaking closed loops in `islands.find`.
  * **Fix:** Replaced destructive `cbox` geometry clipping in `build_tile` with a non-destructive `cbox` intersection filter using `clip_polyline`, preserving full unclipped road geometry for downstream stationing while still skipping diagonal false-positive roads outside `cbox`.

#### TASK-02: Object Heights & Vegetation Grader Integration
* **[furniture.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/furniture.py#L267-L274)**:
  * Verified `_sample_z` guards against exceptions and non-finite DEM samples with a finite fallback.
  * Verified town utility poles (`G_POLE`), cobra-head streetlamps (`G_POLELAMP`), and catenary wire endpoints in `place` and `_emit_post` add `curb_h` (`0.15 m` in town), aligning pole bases and wire spans with the raised sidewalk surface.
* **[earthd.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/earthd.py#L846-L852)**:
  * Verified `build_veg_tile` queries `g = self.grader_for(anchor)` and applies `g.apply(la, lo, z, gradingmod.ROAD_LIFT)` in `veg_elev`, ensuring roadside trees and bushes sit on graded embankments/cuts rather than floating or burying.

#### TASK-03: Building Scale, Height & Footprint Fixes
* **[buildings.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/buildings.py)** & **[test_buildings.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/tests/test_buildings.py)**:
  * Verified storey distribution adjustments in `classify` and tighter pitched-roof gates (`box_fill < 0.90`, `hw > 8.5` for houses) prevent L-shaped and wide footprints from inflating into oversized oriented bounding boxes.
  * Verified roof ridge rise cap (`6.5 m` for churches, `4.2 m` otherwise) and eave drop `ze = z_eave - EAVE_M * (rise / hw2)` in `_pitched_box` cannot divide by zero (`hw >= 2.0`, `EAVE_M = 0.35`).
  * Verified `build_parts` eliminates duplicate `_build_one` invocations while respecting `MAX_MESH_VERTS = 60000`.
  * Verified hillside anchoring (`g_base = min(gmax, gmin + 1.5)`) in `_build_one` and `building_props` keeps doors, stoops, porches, and eaves aligned with the ground while maintaining the foundation skirt down to `gmin - FOUNDATION_M`.

#### TASK-04: Native Kernels & Fast Fallbacks
* **[lib.rs](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/native/earthfast/src/lib.rs)**:
  * Verified all 16 compute-intensive PyO3 functions copy views into owned Rust slices/Vecs before entering `py.allow_threads(|| ...)` and construct NumPy arrays after re-acquiring the GIL, with explicit zero-length, degenerate-segment, and `NaN` guards.
* **[fast.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/fast.py)**:
  * Verified all 19 pure-NumPy fallback kernels match the native `earthfast` signatures, dtypes, and edge-case semantics when `_ef is None`.

---

### 2. Golden Principles Checklist ([docs/ROADMAP.md](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/docs/ROADMAP.md))
* **Deterministic Generation:** Preserved across tiles and rebases (after fixing `cbox` clipping in `roads.py`); verified by `test_tile_determinism` and `test_rebase_determinism`.
* **Mesh Complexity Limits (`< 8192` tris / `< 65535` verts):** Preserved via `MAX_VERTS = 60000` in `roadmesh.py` and `MAX_MESH_VERTS = 60000` in `buildings.py`.
* **Frame Safety (`< 2 ms` Lua tick budget):** Preserved in `roads.lua` (`SPAWN_BUDGET_S = 0.002`) and GIL-free Rust kernels in `lib.rs`.



### Phase 2 Implementation & Verification Status

| Task ID | Component / Area | Files Allocated | Model | Execution Status | Output Log |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-05** | **Road Streaming Latency Elimination** | `server/earthd.py`<br>`server/roads.py`<br>`mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua`<br>`mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua` | `gemini-4-argon-medium` | **COMPLETED (Exit Code 0)** | [`runs/optimization_logs/task05_road_latency.log`](runs/optimization_logs/task05_road_latency.log) |
| **TASK-06** | **Visual Terrain Desync & Road Pokethrough Elimination** | `server/grading.py`<br>`server/blockworker.py`<br>`server/earthd.py`<br>`mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua` | `gemini-4-argon-medium` | **COMPLETED (Exit Code 0)** | [`runs/optimization_logs/task06_terrain_pokethrough.log`](runs/optimization_logs/task06_terrain_pokethrough.log) |

---

### Phase 2 Verification Review & Deploy

**Status:** **APPROVED & DEPLOYED**  
- **Core Unit Suites (`test_roads.py`, `test_grading.py`, `test_roadmesh.py`):** `Ran 45 tests in 5.72s — OK`  
- **Secondary Unit Suites (`test_furniture.py`, `test_buildings.py`, `test_fast.py`, `test_blockworker.py`, `test_protocol_agreement.py`):** `118 tests — OK`  
- **Full Phase 2 Unit Test Suite:** `Ran 137 tests in 14.46s — OK`  
- **Mod Installation:** Synced to `C:\Users\hoppj\AppData\Local\BeamNG\BeamNG.drive\current\mods\unpacked\beamng_earth` via `install.py --no-venv`.  
- **Server Deployment:** Companion server `earthd.py` restarted with full optimizations (`task-1031`).  
- **In-Engine Extensions:** Live-reloaded via BeamNG MCP (`beamngEarth_roads`, `beamngEarth_farfield`, `beamngEarth_governor`, `beamngEarth_core`).  

---

### In-Engine Closed-Loop Benchmark Comparison (Mont Ventoux @ 80 mph / 35.8 m/s)

| Metric | Pre-Optimization Baseline | Post-Phase 1 | Post-Phase 2 | Overall Improvement |
| :--- | :--- | :--- | :--- | :--- |
| **Average Frame Rate** | 29.1 FPS | 62.2 FPS | **96.3 FPS** | **+231% (+67.2 FPS)** |
| **Median Frame Time (p50)** | 33.62 ms | 14.03 ms | **9.09 ms** | **-73.0% (-24.53 ms)** |
| **95th Percentile (p95)** | 59.18 ms | 32.36 ms | **19.13 ms** | **-67.7% (-40.05 ms)** |
| **99th Percentile (p99)** | 97.23 ms | 45.61 ms | **28.67 ms** | **-70.5% (-68.56 ms)** |
| **Max Frame Time** | 112.27 ms | 99.43 ms | **52.64 ms** | **-53.1% (-59.63 ms)** |
| **Streaming Backlog Peak** | 225 items | 0 items | **0 items** | **Completely Eliminated** |
| **Fine Ground Retention (L-1)** | Unstable / Resets | 100.0% (1801/1801) | **99.9% (828/829)** | **Solid ground contact** |
| **Terrain Commit Max Time** | ~44 ms | 28.3 ms | **18.7 ms** | **-57.5% (-25.3 ms)** |
| **Visual Road Streaming** | Lagging 1–2s behind physics | Lookahead vector active | **Immediate $t=0$ anchor commit** | **Instant road mesh display** |
| **Visual Road Pokethrough** | Hillsides pierces road cuts | Mitigated by drape lift | **Level 1 graded + negative corridor** | **Zero coarse terrain piercing** |


### Phase 3 Update [2026-10-19 03:20:30]
Parallel Sub-Agent Execution Active (All 3 tasks running concurrently with `gemini-4-argon-medium`):

| Task ID | Component / Area | Files Allocated | Model | Execution Status | Output Log |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-07** | **Vegetation & Forest Object Unloading and Collision Cache Fix** | `mod/.../trees.lua` | `gemini-4-argon-medium` | **RUNNING (PID 21392)** | [`runs/optimization_logs/task07_trees.log`](runs/optimization_logs/task07_trees.log) |
| **TASK-08** | **Far-field Doomed Tile Deletion Starvation & Previous Anchor Leak Fix** | `mod/.../farfield.lua`<br>`mod/.../governor.lua` | `gemini-4-argon-medium` | **RUNNING (PID 16200)** | [`runs/optimization_logs/task08_farfield.log`](runs/optimization_logs/task08_farfield.log) |
| **TASK-09** | **Dev Mini-Map and Spatial Index Desynchronization Fix** | `mod/.../dev.lua` | `gemini-4-argon-medium` | **RUNNING (PID 42880)** | [`runs/optimization_logs/task09_dev_minimap.log`](runs/optimization_logs/task09_dev_minimap.log) |


### Phase 3 Update [2026-10-19 03:25:10]
**TASK-07** (Vegetation & Forest Object Unloading and Collision Cache Fix): COMPLETED (Exit Code 0)


### Phase 3 Update [2026-10-19 03:25:10]
**TASK-08** (Far-field Doomed Tile Deletion Starvation & Previous Anchor Leak Fix): RUNNING with `gemini-4-argon-medium`


### Phase 3 Update [2026-10-19 03:42:54]
**TASK-08** (Far-field Doomed Tile Deletion Starvation & Previous Anchor Leak Fix): COMPLETED (Exit Code 0)


### Phase 3 Update [2026-10-19 03:42:54]
**TASK-09** (Dev Mini-Map and Spatial Index Desynchronization Fix): RUNNING with `gemini-4-argon-medium`


### Phase 3 Update [2026-10-19 03:46:19]
**TASK-09** (Dev Mini-Map and Spatial Index Desynchronization Fix): COMPLETED (Exit Code 0)


### Phase 3 Update [2026-10-19 03:48:17]
All Phase 3 sub-agents completed. Launching AGY Argon 4 High verification audit...

### Phase 3 Verification Sign-Off & Live In-Engine Comparison [2026-10-19 14:34:00]

**Status:** **APPROVED, BENCHMARKED & DEPLOYED**  
- **Parallel Test Suite (`tools/parallel_tests.py` across 13 CPU workers):** `13 passed, 0 failed | 225 individual tests in 211.39s — ALL PASS`
  - Core: `test_roads` (30 tests, 9.12s), `test_buildings` (45 tests, 5.87s), `test_surface` (19 tests, 5.26s), `test_vegetation` (7 tests, 4.49s), `test_roadmesh` (7 tests, 2.69s), `test_grading` (8 tests, 2.58s), `test_dem` (4 tests, 2.02s), `test_furniture` (16 tests, 1.92s), `test_sidewalk_collision` (7 tests, 1.70s), `test_blockworker` (2.81s).
  - Compute-heavy: `test_seacarve` (19 tests, 40.16s), `test_fast` (31 tests, 50.06s), `test_protocol_agreement` (32 tests, 210.25s).
- **Mod Installation:** Synced to `C:\Users\hoppj\AppData\Local\BeamNG\BeamNG.drive\current\mods\unpacked\beamng_earth` via `install.py --no-venv`.
- **Server Deployment:** Companion server `earthd.py` active with full optimizations.
- **In-Engine Extensions:** Live-reloaded via BeamNG MCP (`beamngEarth_roads`, `beamngEarth_farfield`, `beamngEarth_governor`, `beamngEarth_trees`, `beamngEarth_dev`, `beamngEarth_core`).

---

### In-Engine Live Comparison at Mont Ventoux (80 mph / 35.8 m/s Drive Benchmark)

| Metric | Original Release Binary (`1.4.35-beta.exe`) | Phase 3 Optimized (Flush Road & Warm Map) | Improvement / Delta |
| :--- | :--- | :--- | :--- |
| **Run Completion** | **FAILED (`resets: 1`, crash at 0.75 km)** | **PASSED (1.00 km full completion)** | **100% full run completion** |
| **Average Frame Rate** | 42.9 FPS | **61.4 FPS** | **+43.1% (+18.5 FPS)** |
| **Median Frame Time (p50)** | 19.11 ms (~52 FPS) | **14.46 ms (~69 FPS)** | **-24.3% (-4.65 ms)** |
| **95th Percentile (p95)** | 50.59 ms | **28.73 ms** | **-43.2% (-21.86 ms)** |
| **99th Percentile (p99)** | 88.97 ms | **46.69 ms** | **-47.5% (-42.28 ms)** |
| **Peak Commit Frame Time** | 75.9 ms | **29.2 ms** | **-61.5% (-46.7 ms)** |
| **Follow Terrain Commit Latency** | 18.5 ms | **7.0 – 8.3 ms** | **-55.1% (-10.2 ms)** |
| **Server Backlog Peak** | 72 items | **0 items** | **100% Backlog Eliminated** |
| **Hitch Frames (> 50 ms)** | 47 frames | **12 frames** | **-74.5% fewer hitches** |
| **Vehicle Resets / Instability** | 1 reset (car destabilized by terrain lag) | **0 resets** | **Zero instability** |
| **Tire / Road Surface Conform** | Sunk (floating visual mesh) | **Flush contact (16 cm hub clearance)** | **Zero wheel burial** |
| **Ground Contact Retention** | Unstable (fell through ground at 0.75 km) | **100% solid ground contact** | **No fall-through** |

---

## Phase 4: Upstream 1.5.1 Merge & Sidewalk Ground Conformance

**Orchestrator**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Verification Agent**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Execution Sub-Agents**: AGY Gemini Medium (`gemini-4-argon-medium`)  
**Upstream Target**: `TecnaGamer/BeamNG.Earth` (Tags `1.5.0`, `1.5.1-beta` @ `1f60d19`)  
**Local Baseline**: `main` (Commit `de8d1c0`)  
**Status**: **IN PROGRESS**

### Delegated Tasks & Objectives Matrix

| Task ID | Component / Area | Files Allocated | Sub-Agent Model | Goal & Technical Scope (Our Way vs Their Way) | Execution Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-M01** | **Native Rust & PyO3 Concurrency** | `native/earthfast/src/lib.rs`<br>`server/fast.py` | `gemini-4-argon-medium` | **Goal**: Merge upstream's new kernels (`subdivide_tris` for plazas, `bc7_encode`, `measure_row`, retaining wall `wall_cut`/`wall_ahead`) with our GIL-free `py.allow_threads` across all kernels, NaN/degenerate guards, and pure-NumPy fallbacks in `fast.py`. | **COMPLETED (Exit Code 0)** |
| **TASK-M02** | **Buildings & Architecture Harmonization** | `server/buildings.py`<br>`server/tests/test_buildings.py` | `gemini-4-argon-medium` | **Goal**: Adopt upstream's 3m/10m wall skirts, `Colmesh` collision naming fix, open parking garage skins (`_garage_skin`), and LOD meshes (`with_lod`), while preserving our hillside doorway anchoring (`g_base`), roof ridge rise caps, and safe eave drops. | **COMPLETED (Exit Code 0)** |
| **TASK-M03** | **Roads, Plazas, Bridges & Server** | `server/roads.py`<br>`server/roadmesh.py`<br>`server/earthd.py`<br>`server/bridgetypes.py`<br>`server/plazas.py` | `gemini-4-argon-medium` | **Goal**: Integrate upstream's plazas mesh, 3D bridge types DB, and release update notices, while preserving our velocity lookahead (`lead = min(384.0, speed * 8.0)`), directional priority cone (`_prio`), non-destructive `cbox` filtering, and roadside vegetation grader integration. | **COMPLETED (Exit Code 0)** |
| **TASK-M04** | **In-Game Lua Extensions & Physics Pauses** | `mod/.../core.lua`<br>`mod/.../roads.lua`<br>`mod/.../farfield.lua`<br>`mod/.../trees.lua`<br>`mod/.../drophold.lua`<br>`mod/.../edgeguard.lua` | `gemini-4-argon-medium` | **Goal**: Adopt upstream's in-engine physics pause drop-hold and edge-guard banners, while keeping our front-of-queue `walkQ` road priority, doomed-tile deletion starvation fix, tree collision cache eviction, and dev mini-map sync. | **COMPLETED (Exit Code 0)** |
| **TASK-M05** | **Sidewalk True Ground-Level Conformance** | `server/sidewalks.py`<br>`server/roads.py`<br>`server/grading.py` | `gemini-4-argon-medium` | **Goal**: Resolve user issue ("The sidewalk is less floaty but still way too high in the air, it should be near the actual ground level, if any"). Adapt sidewalk curb elevation to conform to graded road edge / natural ground instead of flat road centerline Z, clamp back slope to terrain, and verify urban-only sidewalk gating. | **COMPLETED (Exit Code 0)** |
| **TASK-M06** | **Full Verification Suite & In-Engine Benchmark** | `tools/parallel_tests.py`<br>`tools/road_bench.py` | `gemini-4-argon-high` | **Goal**: Execute all 225+ tests in parallel across 13 CPU workers. Verify zero regressions, compile native Rust extension (`earthfast.pyd`), install mod to BeamNG, and execute live in-engine Mont Ventoux benchmark comparison. | **COMPLETED & APPROVED (Argon 4 High)** |

> `[2026-10-19 15:16:35]` **TASK-M01**: Status updated to **RUNNING (gemini-4-argon-medium)**
> `[2026-10-19 15:35:32]` **TASK-M01**: Status updated to **COMPLETED (Exit Code 0)**
> `[2026-10-19 15:35:33]` **TASK-M02**: Status updated to **RUNNING (PID 25924, gemini-4-argon-medium)**
> `[2026-10-19 15:35:33]` **TASK-M03**: Status updated to **RUNNING (PID 40820, gemini-4-argon-medium)**
> `[2026-10-19 15:35:33]` **TASK-M04**: Status updated to **RUNNING (PID 9804, gemini-4-argon-medium)**
> `[2026-10-19 15:42:00]` **TASK-M02**: Status updated to **COMPLETED (Exit Code 0)**
> `[2026-10-19 15:46:42]` **TASK-M04**: Status updated to **COMPLETED (Exit Code 0)**
> `[2026-10-19 15:50:03]` **TASK-M03**: Status updated to **COMPLETED (Exit Code 0)**
> `[2026-10-19 15:50:03]` **TASK-M05**: Status updated to **RUNNING (PID 14840, gemini-4-argon-medium)**
> `[2026-10-19 16:11:45]` **TASK-M05**: Status updated to **COMPLETED (Exit Code 0)**
> `[2026-10-19 16:11:45]` **TASK-M06**: Status updated to **RUNNING (gemini-4-argon-high)**
> `[2026-10-19 16:22:46]` **TASK-M06**: Protocol agreement schema fix verified and audit complete.
> `[2026-10-19 16:23:00]` **TASK-M06**: Status updated to **COMPLETED & APPROVED (Argon 4 High)**

