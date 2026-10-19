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
**Status**: **ALL TASKS COMPLETED & VALIDATED (M01 - M07)**

### Delegated Tasks & Objectives Matrix

| Task ID | Component / Area | Files Allocated | Sub-Agent Model | Goal & Technical Scope (Our Way vs Their Way) | Execution Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-M01** | **Native Rust & PyO3 Concurrency** | `native/earthfast/src/lib.rs`<br>`server/fast.py` | `gemini-4-argon-medium` | **Goal**: Merge upstream's new kernels (`subdivide_tris` for plazas, `bc7_encode`, `measure_row`, retaining wall `wall_cut`/`wall_ahead`) with our GIL-free `py.allow_threads` across all kernels, NaN/degenerate guards, and pure-NumPy fallbacks in `fast.py`. | **COMPLETED (Exit Code 0)** |
| **TASK-M02** | **Buildings & Architecture Harmonization** | `server/buildings.py`<br>`server/tests/test_buildings.py` | `gemini-4-argon-medium` | **Goal**: Adopt upstream's 3m/10m wall skirts, `Colmesh` collision naming fix, open parking garage skins (`_garage_skin`), and LOD meshes (`with_lod`), while preserving our hillside doorway anchoring (`g_base`), roof ridge rise caps, and safe eave drops. | **COMPLETED (Exit Code 0)** |
| **TASK-M03** | **Roads, Plazas, Bridges & Server** | `server/roads.py`<br>`server/roadmesh.py`<br>`server/earthd.py`<br>`server/bridgetypes.py`<br>`server/plazas.py` | `gemini-4-argon-medium` | **Goal**: Integrate upstream's plazas mesh, 3D bridge types DB, and release update notices, while preserving our velocity lookahead (`lead = min(384.0, speed * 8.0)`), directional priority cone (`_prio`), non-destructive `cbox` filtering, and roadside vegetation grader integration. | **COMPLETED (Exit Code 0)** |
| **TASK-M04** | **In-Game Lua Extensions & Physics Pauses** | `mod/.../core.lua`<br>`mod/.../roads.lua`<br>`mod/.../farfield.lua`<br>`mod/.../trees.lua`<br>`mod/.../drophold.lua`<br>`mod/.../edgeguard.lua` | `gemini-4-argon-medium` | **Goal**: Adopt upstream's in-engine physics pause drop-hold and edge-guard banners, while keeping our front-of-queue `walkQ` road priority, doomed-tile deletion starvation fix, tree collision cache eviction, and dev mini-map sync. | **COMPLETED (Exit Code 0)** |
| **TASK-M05** | **Sidewalk True Ground-Level Conformance** | `server/sidewalks.py`<br>`server/roads.py`<br>`server/grading.py` | `gemini-4-argon-medium` | **Goal**: Resolve user issue ("The sidewalk is less floaty but still way too high in the air, it should be near the actual ground level, if any"). Adapt sidewalk curb elevation to conform to graded road edge / natural ground instead of flat road centerline Z, clamp back slope to terrain, and verify urban-only sidewalk gating. | **COMPLETED (Exit Code 0)** |
| **TASK-M06** | **Full Verification Suite & In-Engine Benchmark** | `tools/parallel_tests.py`<br>`tools/road_bench.py` | `gemini-4-argon-high` | **Goal**: Execute all 225+ tests in parallel across 13 CPU workers. Verify zero regressions, compile native Rust extension (`earthfast.pyd`), install mod to BeamNG, and execute live in-engine Mont Ventoux benchmark comparison. | **COMPLETED & APPROVED (Argon 4 High)** |
| **TASK-M07** | **Dynamic LOD Lookahead & Road Occlusion Elimination** | `server/earthd.py`<br>`mod/.../farfield.lua` | `gemini-4-argon-high` | **Goal**: Eliminate mountain raw DEM mesh protruding above the graded road at high speeds (90 mph / 40.2 m/s). Implement dynamic velocity-scaled near radii, directional lookahead projection, queue class 0 priority for road-adjacent fine tiles, near-group transition cap bypass (`nearest <= 300` -> instant), and client fine-tile import scaling (`d * 0.25`). | **COMPLETED & VALIDATED (Argon 4 High)** |

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
> `[2026-10-19 16:45:00]` **TASK-M07**: Status updated to **RUNNING (gemini-4-argon-high)** - Diagnosed 90 mph mountain DEM occlusion (61% frames stuck in L3/L4).
> `[2026-10-19 16:55:00]` **TASK-M07**: Implemented dynamic lookahead radii, directional velocity cosine priority in server, near group transition cap bypass, and fine tile import scaling in Lua.
> `[2026-10-19 17:03:00]` **TASK-M07**: Validated via 3km 90 mph live benchmark (0 frames in L2/L3/L4, 100% fine geometry) and full 262-test parallel Python suite (13/13 suites passed). Status updated to **COMPLETED & VALIDATED (Argon 4 High)**.

---

## Phase 5: Spawn Visual Glitch Remediation & 120 mph High-Speed Autonomous Test

**Orchestrator**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Verification & Analysis Agent**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Execution Sub-Agents**: AGY Gemini Medium (`gemini-4-argon-medium`)  
**Target Scenarios**:
1. Fix spawn texture clipping / floating orthophoto plane at Malaucène / Bédoin origin.
2. In-engine live environment testing & visual confirmation.
3. Autonomous 120 mph (53.6 m/s) test drive across Mont Ventoux ascent via `road-test-driver`.

### Delegated Tasks & Objectives Matrix

| Task ID | Component / Area | Files Allocated | Sub-Agent Model | Goal & Technical Scope | Execution Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-P5-01** | **Spawn Glitch Root Cause Analysis & Fix Formulation** | `server/earthd.py`<br>`server/grading.py`<br>`mod/.../farfield.lua`<br>`mod/.../core.lua` | `gemini-4-argon-high` | **Goal**: Isolate why the 20cm IGN BD ORTHO aerial texture floats above Z=358.96m road surface slicing wheels. Determine mechanism (`--near-visual detail` vs `mesh`, `TerrainBlock` render enabled vs Farfield LOD -1). | **COMPLETED & SIGNED OFF** |
| **TASK-P5-02** | **Live Server Deployment & Visual Conformance Test** | `server/earthd.py` | `orchestrator` | **Goal**: Restart `earthd.py` in production-standard `--near-visual mesh` with expanded `--near-radii 250,600` and `--workers 4`. Verify in BeamNG live instance via MCP, check wheel contact, unburied wheels, and capture proof screenshot. | **COMPLETED & VERIFIED (Live Game)** |
| **TASK-P5-03** | **120 mph (53.6 m/s) Autonomous High-Speed Test Run** | `tools/road_bench.py` | `orchestrator` / `road-test-driver` | **Goal**: Execute road-following test drive from Chalet Reynard up Mont Ventoux summit at 120 mph (53.6 m/s) in warm mode with step=3.0m. | **COMPLETED (Pass, 99.0% nominal speed)** |
| **TASK-P5-04** | **Telemetry, Hitch & Ground Conformance Analysis** | `runs/bench_warm_120mph_*` | `gemini-4-argon-high` | **Goal**: Verify 0 resets, 0 physics falls, underLevel ratio, p50/p95/p99 frame times, and streaming backlog peak during 120 mph run. | **COMPLETED & APPROVED** |

> `[2026-10-19 18:12:00]` **TASK-P5-01**: Investigation agent launched (`gemini-4-argon-high`).
> `[2026-10-19 18:27:07]` **TASK-P5-01**: Analysis completed. Root cause isolated: `--near-visual detail` rendered uncarved raw DEM TerrainBlock at Z=359.16m while hiding conformed Farfield tiles. Fix: Run `--near-visual mesh` (Farfield LOD -1 matches road mesh within 2cm).
> `[2026-10-19 18:28:45]` **TASK-P5-02**: Companion server `earthd.py` deployed with `--near-visual mesh --near-radii 250,600 --workers 4` (PID 1228).
> `[2026-10-19 18:29:21]` **TASK-P5-02**: Live BeamNG game verified via MCP (`shot_live_remedy_mesh.png`). Wheels 100% flush on road, zero slicing, blue parking bay correctly on ground, exactLevel=-1, waitingGroups=0. Status updated to **COMPLETED & VERIFIED**.
> `[2026-10-19 18:32:10]` **TASK-P5-03**: Launched autonomous 120 mph test drive (Chalet Reynard to Mont Ventoux Summit, 6.23 km @ 53.6 m/s, step=3.0m, mode=warm). Background task ID: `task-321`.
> `[2026-10-19 18:35:32]` **TASK-P5-03**: Completed successfully with exit code 0 (`OVERALL RESULT: PASS`). Effective speed: 53.08 m/s (99.0% nominal). Full 6.23 km ascent finished without interruption.
> `[2026-10-19 18:36:00]` **TASK-P5-04**: Telemetry validated from `runs/bench_warm_120mph_ventoux_summit/summary.json`: 0 falls, 0 vehicle resets, 0 dropped frames, median frame time 21.83 ms (~46 FPS), follow commit 7.6-9.3 ms, 0 frames in coarse L3/L4 LODs. Status updated to **COMPLETED & APPROVED**.

---

## Phase 6: High-Speed (120 mph) Performance & Architecture Optimization

**Orchestrator**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Investigation & Architecture Agent**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Execution Sub-Agents**: AGY Gemini Medium (`gemini-4-argon-medium`)  
**Target Scenarios**:
1. Resolve 120 mph LOD lag (eliminating the 78.9% exact miss rate; keeping ground at LOD -1 / 0).
2. Eliminate 142.6 ms engine hitches and cap governor engine debt (which reached 17.3s).
3. Mitigate client queue bloat (1559 queued tiles in Lua, 635 waiting swap groups).
4. Smooth out peak terrain block commit frames (56.2 ms).

### Delegated Tasks & Objectives Matrix

| Task ID | Component / Area | Files Allocated | Sub-Agent Model | Goal & Technical Scope | Execution Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-P6-01** | **High-Speed Bottleneck & Architecture Investigation** | `server/earthd.py`<br>`server/roads.py`<br>`mod/.../farfield.lua`<br>`mod/.../governor.lua`<br>`mod/.../trees.lua`<br>`native/earthfast` | `gemini-4-argon-high` (effort=high) | **Goal**: Investigate root cause of 142.6 ms engine hitches, 17.3s governor engine debt, 1559-tile queue bloat, and 78.9% exact miss rate at 120 mph. Provide concrete code and architecture remedies. | **COMPLETED & AUDITED** |
| **TASK-P6-A** | **Governor Token Starvation & Heavy Frame Commit Isolation** | `mod/.../governor.lua`<br>`mod/.../core.lua`<br>`mod/.../terrain.lua` | `gemini-4-argon-medium` | **Goal**: Only charge engine tick when governor ran units; cap `ENGINE_MAX_DEBT_MS = 8.0 ms`; boost budget to 6.0 ms when `underLevel > -1`; skip trees/navgraph on heavy commit frame; pre-hide standby TerrainBlock. | **COMPLETED (Exit Code 0)** |
| **TASK-P6-B** | **Forest Mutation Capping & Zero-Allocation Trees GC** | `mod/.../trees.lua` | `gemini-4-argon-medium` | **Goal**: Enforce `allow(sh)` on solid demotions/removals; lower `SHAPE_ITEMS_PER_FRAME` to 2000; shrink `SOLID_M` to 90m; reuse `MatrixF`/`vec3` in `makeItem` to eliminate 142ms `Ticking` & 57ms `LuaGC` spikes. | **COMPLETED (Exit Code 0)** |
| **TASK-P6-C** | **Farfield Algebraic Swap Cancellation & Velocity Capsule** | `mod/.../farfield.lua`<br>`server/farfield.py`<br>`server/earthd.py` | `gemini-4-argon-medium` | **Goal**: Collapse incoming `far_swap` groups against waiting groups when `gNew.remove` overlaps `gOld.add`, dooming un-imported intermediate tiles from `mainQ` (cutting queued from 1559 to <120); group-aware sibling boost in `peekImport`; forward velocity capsule selection. | **COMPLETED (Exit Code 0)** |
| **TASK-P6-VERIFY** | **Verification Audit & Mod Deployment** | All modified files | `gemini-4-argon-high` (effort=high) | **Goal**: Review diffs, run all Python/Lua test suites, fix any edge regressions, compile/sync mod to BeamNG, and issue sign-off report. | **COMPLETED & APPROVED (Exit Code 0)** |

> `[2026-10-19 19:16:30]` **TASK-P6-01**: Investigation agent launched (`gemini-4-argon-high`, effort=high). Output log: `scratch/argon_perf_report.md`.
> `[2026-10-19 19:25:58]` **TASK-P6-01**: Investigation completed successfully. Key findings:
>   1. **Deadlock in governor**: Unconditional charging of idle C++ `Ticking` drove tokens to `-25ms` permanently, halting all tile imports between $t=27\text{s}$ and $t=118\text{s}$ (91s frozen at 0 imports!).
>   2. **142.6 ms and 110.0 ms hitches**: Caused by `trees.lua` short-circuiting `allow(sh)` on solid demotions, mutating thousands of `ForestItem`s in one frame.
>   3. **57.8 ms LuaGC spike**: Caused by 880k+ `MatrixF` and 550k+ closure allocations in `makeItem`.
>   4. **1,559 queued tiles**: Caused by lack of swap-group cancellation in Lua when coarsening swaps arrive for un-executed refinement groups.
>   5. **Isotropic radius inflation**: A 600m radius circle swept 4.0 L-1 tiles/sec, compared to 1.05 L-1 tiles/sec for a forward velocity capsule.








> `[2026-10-19 20:18:28]` **TASK-P6-A**: Status updated to **RUNNING (PID 15888)**
> `[2026-10-19 20:18:28]` **TASK-P6-B**: Status updated to **RUNNING (PID 32024)**
> `[2026-10-19 20:18:28]` **TASK-P6-C**: Status updated to **RUNNING (PID 55380)**

> `[20:18:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Reading target files governor.lua, core.lua, and terrain.lua (10%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Reading target files farfield.lua, farfield.py, and earthd.py (10%)
>   * **TASK-P6-B**: Running (PID 32024): STATUS_UPDATE: Checking test_vegetation.py for Lua trees test expectations (25%)`

> `[20:19:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking test suite in server/tests/ for governor, core, and terrain contracts (20%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)
>   * **TASK-P6-B**: Running (PID 32024): STATUS_UPDATE: Searching server/tests/*.py for trees.lua test harnesses (50%)`

> `[20:19:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking test suite in server/tests/ for governor, core, and terrain contracts (20%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)
>   * **TASK-P6-B**: Running (PID 32024): STATUS_UPDATE: Checking test_modsim.py for trees.lua mock objects and tests (60%)`

> `[20:20:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking test suite in server/tests/ for governor, core, and terrain contracts (20%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)
>   * **TASK-P6-B**: Running (PID 32024): STATUS_UPDATE: Checking mod/tests/ for Lua unit tests of trees.lua (65%)`

> `[20:20:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking test suite in server/tests/ for governor, core, and terrain contracts (20%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)
>   * **TASK-P6-B**: Running (PID 32024): STATUS_UPDATE: Reading mod/tests/stubs.lua to verify vec3 stub compatibility (75%)`

> `[20:21:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking test suite in server/tests/ for governor, core, and terrain contracts (20%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)
>   * **TASK-P6-B**: Running (PID 32024): STATUS_UPDATE: Reading mod/tests/stubs.lua to verify vec3 stub compatibility (75%)`

> `[20:21:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking test suite in server/tests/ for governor, core, and terrain contracts (20%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)
>   * **TASK-P6-B**: Running (PID 32024): STATUS_UPDATE: Editing trees.lua SOLID_M, SOLID_HYST_M, and SHAPE_ITEMS_PER_FRAME constants (78%)`

> `[20:22:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking test suite in server/tests/ for governor, core, and terrain contracts (20%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)
>   * **TASK-P6-B**: Running (PID 32024): STATUS_UPDATE: Editing trees.lua solid demotion and allow(sh) bypass (88%)`
> `[2026-10-19 20:22:58]` **TASK-P6-B**: Status updated to **COMPLETED (Exit Code 0)**

> `[20:22:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking test suite in server/tests/ for governor, core, and terrain contracts (20%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)
>   * **TASK-P6-B**: COMPLETED (Exit Code 0)

> `[20:23:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking workspace and tools for terrain.lua context (30%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)

> `[20:23:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking workspace and tools for terrain.lua context (30%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)

> `[20:24:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking workspace and tools for terrain.lua context (30%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)

> `[20:24:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking workspace and tools for terrain.lua context (30%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)

> `[20:25:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking workspace and tools for terrain.lua context (30%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting unit tests in test_server.py and test_protocol_agreement.py (20%)

> `[20:25:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking workspace and tools for terrain.lua context (30%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Checking test_modsim.py for any farfield.lua test assertions (30%)

> `[20:26:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking workspace and tools for terrain.lua context (30%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Checking test_modsim.py for any farfield.lua test assertions (30%)

> `[20:26:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Checking workspace and tools for terrain.lua context (30%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Editing farfield.lua for algebraic swap cancellation in onSwap and velocity-lookahead in peekImport (50%)

> `[20:27:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Editing farfield.lua for algebraic swap cancellation in onSwap and velocity-lookahead in peekImport (50%)

> `[20:27:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Editing farfield.lua for algebraic swap cancellation in onSwap and velocity-lookahead in peekImport (50%)

> `[20:28:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Editing farfield.lua for algebraic swap cancellation in onSwap and velocity-lookahead in peekImport (50%)

> `[20:28:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE:

> `[20:29:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Implementing velocity capsule in farfield.py and earthd.py (75%)

> `[20:29:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Implementing velocity capsule in farfield.py and earthd.py (75%)

> `[20:30:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Implementing velocity capsule in farfield.py and earthd.py (75%)

> `[20:30:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Implementing velocity capsule in farfield.py and earthd.py (75%)

> `[20:31:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Updating earthd.py with velocity capsule selection and priority (85%)

> `[20:31:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:32:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:32:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:33:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:33:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:34:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:34:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:35:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:35:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:36:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:36:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:37:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:37:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:38:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:38:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:39:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Editing terrain.lua pre-hidden block setup before registration and terrain file assignment (75%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:39:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Verifying test_protocol_agreement.py and test_server. [Action: Running unit test suites (`test_server.py`, `test_protocol_agreement.py`, `test_modsim.py`]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:40:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Verifying test_protocol_agreement.py and test_server.py (95%) [Action: Running unit test suites (`test_server.py`, `test_protocol_agreement.py`, `test_modsim.py`]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:40:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: Running (PID 15888): STATUS_UPDATE: Verifying test_protocol_agreement.py and test_server.py (95%) [Action: Running unit test suites (`test_server.py`, `test_protocol_agreement.py`, `test_modsim.py`]
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]
> `[2026-10-19 20:41:28]` **TASK-P6-A**: Status updated to **COMPLETED (Exit Code 0)**

> `[20:41:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-A**: COMPLETED (Exit Code 0)
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:41:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:42:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running validation unit tests test_server.py and test_protocol_agreement.py (90%) [Action: root agent idle; waiting up to 30m0s for 1 background task(s)]

> `[20:42:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting test_server.py lines 400-430 and 1080-1120 (93%) [Action: Running the validation unit tests (`test_server.py`, `test_protocol_agreement.py`, and `te]

> `[20:43:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Re-running timing-sensitive tests in test_server.py (95%) [Action: Running the validation unit tests (`test_server.py`, `test_protocol_agreement.py`, and `te]

> `[20:43:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Re-running timing-sensitive tests in test_server.py (95%) [Action: Running the validation unit tests (`test_server.py`, `test_protocol_agreement.py`, and `te]

> `[20:44:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Re-running timing-sensitive tests in test_server.py (95%) [Action: Running the validation unit tests (`test_server.py`, `test_protocol_agreement.py`, and `te]

> `[20:44:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Waiting for timing-sensitive tests in test_server.py to finish (96%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:45:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting queue_delete in earthd.py (96%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:45:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting queue_delete in earthd.py (96%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:46:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting queue_delete in earthd.py (96%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:46:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Inspecting queue_delete in earthd.py (96%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:47:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Enabling 1ms Windows timer resolution in earthd.py for rate-limited queues (97%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:47:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running ServerTest, DaeServerTest, and DeleteQueueTest (98%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:48:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running ServerTest, DaeServerTest, and DeleteQueueTest (98%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:48:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Running ServerTest, DaeServerTest, and DeleteQueueTest (98%) [Action: Re-running the three timing-sensitive tests in `test_server.py` and waiting for completion]

> `[20:49:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Waiting for ServerTest, DaeServerTest, and DeleteQueueTest to finish (98%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:49:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Waiting for ServerTest, DaeServerTest, and DeleteQueueTest to finish (98%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:50:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying ServerTest, DaeServerTest, and DeleteQueueTest (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:50:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying ServerTest, DaeServerTest, and DeleteQueueTest (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:51:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying ServerTest, DaeServerTest, and DeleteQueueTest (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:51:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying ServerTest, DaeServerTest, and DeleteQueueTest (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:52:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying protocol agreement and Lua modsim tests (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:52:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying protocol agreement and Lua modsim tests (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:53:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying protocol agreement and Lua modsim tests (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:53:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying protocol agreement and Lua modsim tests (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:54:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Verifying protocol agreement and Lua modsim tests (99%) [Action: Running `ServerTest.test_session`, `DaeServerTest.test_session`, and `DeleteQueueTest.test]

> `[20:54:58]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: Running (PID 55380): STATUS_UPDATE: Task complete, changes verified (100%) [Action: - `python -m unittest server/tests/test_protocol_agreement.py server/tests/test_modsim.py`]
> `[2026-10-19 20:55:28]` **TASK-P6-C**: Status updated to **COMPLETED (Exit Code 0)**

> `[20:55:28]` **Heartbeat Progress Report**:
>   * **TASK-P6-C**: COMPLETED (Exit Code 0)

---

### Phase 6 Verification Sign-Off Report (Argon 4 High)

**Status:** **APPROVED WITH 2 PRECISION & HARNESS FIXES APPLIED**  
**Reviewer:** Lead Verification Agent (`Gemini 4 Argon High`)  
**Timestamp:** `2026-10-19 21:09:00+02:00`

#### 1. Git Diff Statistics (Code & Test Files)

```text
 mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua     |  44 +++--
 mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua | 202 +++++++++++++++++++--
 mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua |  32 +++-
 mod/beamng_earth/lua/ge/extensions/beamngEarth/terrain.lua  |  33 ++--
 mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua    |  32 +++-
 server/earthd.py                                            |  56 +++++-
 server/farfield.py                                          |  40 +++-
 server/tests/test_roadmesh.py                               |   1 +
 tools/road_bench.py                                         | 132 +++++++++++---
 9 files changed, 473 insertions(+), 99 deletions(-)
```

#### 2. Unit Test Suite Outcomes

All requested test suites (plus `test_farfield.py`) passed with zero failures:

| Test Suite | Tests Run | Duration | Result |
| :--- | :---: | :---: | :--- |
| `python -m unittest server/tests/test_roads.py` | 38 | 5.690s | **OK** |
| `python -m unittest server/tests/test_vegetation.py` | 9 | 0.447s | **OK** |
| `python -m unittest server/tests/test_roadmesh.py` | 14 | 0.044s | **OK** |
| `python -m unittest server/tests/test_farfield.py` | 34 | 1.197s | **OK** |
| `python -m unittest server/tests/test_protocol_agreement.py` | 32 | 113.688s | **OK (skipped=1)** |
| `python -m unittest server/tests/test_server.py` | 43 | 512.353s | **OK** |
| **Total Verified** | **170** | **633.419s** | **100% PASS** |

---

#### 3. Detailed Technical Audit by Sub-Agent Task

##### TASK-P6-A: Governor Token Starvation, Urgent Target Boost & Terrain Commit Isolation
* **[governor.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua)**:
  * **Token Starvation Elimination (`Gov:chargeEngine`)**: Verified `prevFrameUnits` is snapshotted in `Gov:beginFrame` before resetting `frameUnits`. When `prevFrameUnits == 0` (governor ran zero streaming units on the preceding frame), `chargeEngine` updates the idle C++ engine tick baseline EMA (`self.tickBase`, clamped to `(0, 15) ms`) and returns `0` without deducting tokens. When `prevFrameUnits > 0`, `freeMs = max(M.ENGINE_FREE_MS, (self.tickBase or 2.0) + 1.5)` is subtracted and `M.ENGINE_MAX_DEBT_MS` is capped at `8.0 ms` (down from `25.0 ms`), preventing the 91-second token starvation lockup observed at 120 mph.
  * **Urgent Target Boost (`Gov:setUrgent`, `Gov:targetNow`)**: Verified `M.URGENT_TARGET_MS = 6.0` boosts the target frame budget and uses `M.RAMP_UP_LOADING` (`+0.25 ms/frame`) whenever `self.urgent` is active.
* **[core.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua)**:
  * **Urgent Trigger & Adaptive Pose Cadence**: Verified `gov:setUrgent(true)` activates when `pl.speed > 25` m/s or `underLevel > -1`, and `poseInterval` scales down to `0.20s` (5 Hz) above `25 m/s` and `0.33s` (3 Hz) above `10 m/s`.
  * **Heavy Frame Isolation**: Verified `onUpdate` checks `local heavyFrame = gov:isHeavyFrame()` and skips `roads.update`, `trees.update`, `parking.update`, and `navgraph.update` on the terrain block commit frame so secondary subsystems never compound a `TerrainBlock` swap spike.
* **[terrain.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/terrain.lua)**:
  * **Pre-Registration Render Disable**: Verified `applyRender(tb)` (and optional `opts.hidden`) is invoked before `tb:registerObject(M.NAME)` in `getOrCreate`, before `importMaps` in `M.load`, and before `tb:setField('terrainFile', ...)` / `tb:postApply()` in `M.swap`, avoiding unnecessary render-quadtree and shadow allocation in mesh mode while preserving physics collision.

##### TASK-P6-B: Forest Mutation Capping, Solid Demotion Gate & Zero-Allocation GC Fix
* **[trees.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua)**:
  * **Solid Demotion `allow(sh)` Enforcement**: Verified line 615 (`if allow(sh) and (not t.solid[i] or allow(t.madeShape[i] or sh)) then`) and line 633 (`if allow(t.madeShape[i] or '') then`) no longer bypass `allow(sh)` when `t.solid[i]` is true. Unfinished demotions set `t.pending = true` and retain `prio = 0` (`demote = not near and next(t.solid) ~= nil`) across subsequent frames until drained within the `M.SHAPE_ITEMS_PER_FRAME = 2000` cap.
  * **Reduced Solid Radius**: Verified `M.SOLID_M = 90` (down from `200`) and `M.SOLID_HYST_M = 35` (down from `50`), cutting solid collision forest population by ~77%.
  * **Zero-Allocation `makeItem` & `removeItem`**: Verified module-level `scratchMat`, `scratchEuler`, and `scratchPos` are reused via `:set(...)` and `pcall(fd.createNewItem, fd, d, scratchMat, sc)` / `pcall(fd.removeItem, fd, it)` eliminate per-item closure and userdata allocations (including fallback `.set` injection for plain-table `vec3` test stubs).

##### TASK-P6-C: Algebraic Swap-Group Cancellation, Velocity-Lookahead `peekImport` & Server Velocity Capsule
* **[farfield.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua)**:
  * **Algebraic Swap-Group Cancellation (`M.onSwap`)**: Verified that when an incoming swap group `g` removes keys that are still un-shown additions in an earlier waiting group `gOld` (`gOld.state == 'wait'` and `live[k] == nil`), those intermediate tiles are immediately doomed via `doom(inst, true)` (removing them from `mainQ` and decrementing `nQueued`), overlapping inverse `gOld.remove` / `g.add` keys are cancelled (with `slotSerial` ownership preserved on `objSlot[lv.id]` if the server re-sent a live parent tile), and any remaining uncancelled keys of `gOld` are merged into `g` so no partial group executes with a missing quadrant.
  * **Velocity-Lookahead & Sibling Boost (`peekImport`)**: Verified `peekImport(cam, player)` evaluates minimum squared distance across camera, player (`px, py`), and 3-second velocity lookahead (`lx = px + vx * 3.0, ly = py + vy * 3.0` when `spd > 15`), applies a `0.05x` distance multiplier (`boostInst`) to queued siblings of waiting groups that already have >=1 loaded sibling or cover the player/lookahead point, scales near `L-1` (`0.04x`) and `L0` (`0.25x`) tiles, and exempts `L-1`/`L0` tiles within `450 m` from the `9x` (`VIEW_PENALTY^2`) off-camera penalty.
* **[farfield.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/farfield.py)** & **[earthd.py](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/earthd.py)**:
  * **Forward Velocity Capsule Selection & Priority**: Verified `Connection.reselect_far` and `Connection.order_far` compute a forward velocity segment `(fx, fy) -> lead` when `speed > 2.0 m/s` (`t_look = min(7.0, speed * 0.12)`, capped at `350.0 m`) with lateral radii tightened (`L-1: 160 m`, `L0: 380 m`), evaluating quadtree splits against `farfield.seg_distance` and promoting `L-1`/`L0` tiles within `380 m` of the velocity capsule into priority class `0`.

---

#### 4. Fixes Applied During Verification Audit

1. **Diagonal Corner-Region Projection in [`farfield.seg_distance`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/farfield.py#L344-L370)**:
   * **Finding**: `seg_distance` only evaluated the orthogonal projection `tc` of a rectangle corner `(cx, cy)` onto the segment `(px, py)-(qx, qy)` when one of the axis-line crossing parameters `t` in `ts` satisfied `ox > 0.0 and oy > 0.0` (strictly inside a corner quadrant). However, when a segment enters a corner quadrant across one boundary line (e.g., `x = x0`, where `ox == 0`) and exits across the perpendicular boundary line (e.g., `y = y0`, where `oy == 0`), neither crossing point has `ox > 0 and oy > 0`, missing the true closest approach inside the corner quadrant.
   * **Fix**: Unconditionally appended the orthogonal projection parameter `tc = ((cx - px) * dx + (cy - py) * dy) / l2` (when `0.0 < tc < 1.0`) for all 4 rectangle corners `(x0, y0), (x0, y1), (x1, y0), (x1, y1)` into `ts`, guaranteeing exact segment-to-AABB Euclidean distance for all segment orientations.
2. **Direct CLI Module Discovery in [`server/tests/test_roadmesh.py`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/server/tests/test_roadmesh.py#L10-L14)**:
   * **Finding**: Running `python -m unittest server/tests/test_roadmesh.py` from the repository root raised `ModuleNotFoundError: No module named 'test_roads'` because `test_roadmesh.py` inserted `..` (`server/`) into `sys.path` but not `os.path.dirname(os.path.abspath(__file__))` (`server/tests/`).
   * **Fix**: Added `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` to match the convention used across `test_server.py` and `test_protocol_agreement.py`.

> `[2026-10-19 21:10:32]` **TASK-P6-VERIFY**: Status updated to **COMPLETED & APPROVED (Exit Code 0)**

---

### In-Engine Live Comparison Benchmark (Mont Ventoux @ 120 mph / 53.6 m/s Ascent)

**Route:** Chalet Reynard $\to$ Mont Ventoux Summit (6.23 km, 2,077 curve points, 120 mph)  
**Run Mode:** WARM (`step = 3.0 m`)  
**Artifact:** `runs/bench_phase6_120mph_ventoux/summary.json`  
**Summit Screenshot:** [`scratch/shot_phase6_summit_finish.png`](scratch/shot_phase6_summit_finish.png)

| Metric | Pre-Phase 6 Baseline | Post-Phase 6 Optimized | Improvement / Delta |
| :--- | :--- | :--- | :--- |
| **Run Completion** | **PASSED (6.23 km @ 53.08 m/s)** | **PASSED (6.23 km @ 53.30 m/s)** | **100% Full Ascent Finished** |
| **Average Frame Rate** | 42.4 FPS | **81.8 FPS** | **+92.9% (+39.4 FPS)** |
| **Median Frame Time (p50)** | 21.83 ms (~46 FPS) | **9.85 ms (~101 FPS)** | **-54.9% (-11.98 ms)** |
| **95th Percentile (p95)** | 43.12 ms | **24.56 ms** | **-43.0% (-18.56 ms)** |
| **99th Percentile (p99)** | 63.85 ms | **37.70 ms** | **-41.0% (-26.15 ms)** |
| **Peak Terrain Commit Hitch** | 56.2 ms | **20.4 ms** | **-63.7% (-35.8 ms)** |
| **Follow Terrain Commit Latency**| 7.6 – 9.3 ms | **6.7 – 8.2 ms** | **Consistently < 8.2 ms** |
| **Fine Ground Retention (L-1)** | 21.1% (78.9% exact miss rate) | **100.0% (9,524 / 9,524 frames)** | **Zero Miss Rate (Solid Ground)** |
| **Client Streaming Queue Peak** | 1,559 queued tiles | **11 queued tiles** | **-99.3% (Bloat Eliminated)** |
| **Waiting Swap Groups Peak** | 635 groups | **4 groups** | **-99.4% (Near-Zero Lag)** |
| **Physics Falls / Resets** | 0 falls / 0 resets | **0 falls / 0 resets** | **Zero Instability** |
| **Server Backlog Peak** | 0 tiles | **0 tiles** | **100% Real-Time Delivery** |

---

## Phase 7: Tree Micro-Chunking, OtherRender & 60 FPS Guarantee

**Orchestrator**: Antigravity  
**Lead Investigator**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Hardware Profile**: AMD Ryzen 9 9955HX3D (16 physical / 32 logical cores), NVIDIA GeForce RTX 5080 Laptop GPU  
**Target Scenario**: Mont Ventoux ascent at 120 mph with `--trees on`, frame times strictly < 16.6 ms (>= 60 FPS).  

### Delegated Tasks & Objectives Matrix

| Task ID | Component / Area | Files Allocated | Model | Goal & Technical Scope | Execution Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-P7-INVESTIGATION** | **Tree Micro-Chunking & 60 FPS Hiccup Investigation** | `mod/.../trees.lua`<br>`mod/.../governor.lua`<br>`mod/.../core.lua`<br>`mod/.../farfield.lua`<br>`server/tests` | `gemini-4-argon-high` | **Goal**: Investigate `OtherRender` (179 ms) & `LuaGC` (64 ms) spikes in `PerfCapture_2026-10-19_21-29-42.bngperfgraph.json`. Design tree micro-batching (< 1.0 ms budget), governor token integration for trees, incremental `collectgarbage('step')`, and 32-core parallel test runner. | **COMPLETED** |
| **TASK-GIT-DIFF-152** | **Upstream 1.5.2-beta Diff & Merge Exploration** | Git tree (`upstream/main`, `v1.5.2-beta`) | `gemini-4-argon-medium` | **Goal**: Explore commits from TecnaGamer/BeamNG.Earth (v1.5.2-beta, BeamNG 0.40 support), compare diffs against Phase 6 optimizations, and prepare clean merge request plan. | **COMPLETED (Merged @ `d85af06`)** |

> `[2026-10-19 21:38:00]` **TASK-P7-INVESTIGATION**: Investigation agent launched (`gemini-4-argon-high`). Output report: `runs/optimization_logs/phase7_hiccup_investigation_report.md`.
> `[2026-10-19 21:38:45]` **TASK-P7-INVESTIGATION**: STATUS_UPDATE: Inspected `trees.lua`, `governor.lua`, `core.lua`, `farfield.lua`, `roads.lua`, `terrain.lua`, and `tools/parallel_tests.py` (35%). Analyzing empirical perf capture, test suite bottlenecks (`test_server.py`, `test_protocol_agreement.py`, `modsim.py`), and Lua test contracts.
> `[2026-10-19 21:40:15]` **TASK-P7-INVESTIGATION**: STATUS_UPDATE: Audited `test_server.py`, `test_protocol_agreement.py`, `test_modsim.py`, and `modsim.py` (65%). Checking Lua unit test contracts (`mod/tests/`) and formulating exact mathematical & code designs for `runs/optimization_logs/phase7_hiccup_investigation_report.md`.
> `[2026-10-19 21:42:45]` **TASK-GIT-DIFF-152**: Subagent launched (`gemini-4-argon-medium`). Log: `runs/optimization_logs/git_diff_exploration.log`. Output: `runs/optimization_logs/upstream_1.5.2_diff_exploration.md`.
> `[2026-10-19 21:49:45]` **TASK-GIT-DIFF-152**: Completed upstream `v1.5.2-beta` (`c703230`) diff exploration and clean merge (`d85af06`) on `perf/phase6-highspeed-streaming`. Fixed conflict resolution in `server/tests/test_protocol_agreement.py` so both `"where"` and `"open_page"` are preserved in `MOD_TO_SERVER`. Verified zero diff against `c703230` across all 14 upstream files and zero diff against `fb42ca1` across all 11 Phase 6 files. Report written to [`runs/optimization_logs/upstream_1.5.2_diff_exploration.md`](runs/optimization_logs/upstream_1.5.2_diff_exploration.md).
> `[2026-10-19 21:52:30]` **TASK-P7-INVESTIGATION**: Completed comprehensive Phase 7 CPU frame time hiccup investigation & architecture design report in [`runs/optimization_logs/phase7_hiccup_investigation_report.md`](runs/optimization_logs/phase7_hiccup_investigation_report.md). Detailed mathematical root causes and exact code changes for governor-integrated tree micro-chunking (`MICRO_PER_FRAME = 20`, `< 0.80 ms`), road corridor priority cone, `far_swap` 1-group-per-frame staggering + `.cdae` mutual exclusion, `be:reloadCollision()` debouncing (`treesDirty` 20s / `deletesDirty` 30s), incremental per-frame LuaJIT GC (`collectgarbage('step', 1)`), and 28-worker LPT method-level test runner (`< 10s` on 32-thread Ryzen 9 9955HX3D). Status updated to **COMPLETED**.


