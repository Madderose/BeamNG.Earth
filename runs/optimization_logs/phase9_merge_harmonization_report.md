# Phase 9: Merge Harmonization Report (`upstream/main` v1.5.4-beta + High-Speed Streaming Pipeline)

**Author**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  
**Date**: 2026-10-21  
**Upstream Base Target**: `TecnaGamer/BeamNG.Earth` @ `upstream/main` (`bd9c764`, `VERSION` = `1.5.4-beta`)  
**Local Source Branch**: `Madderose/BeamNG.Earth` @ `perf/phase6-highspeed-streaming` (`15bdb0f`, `VERSION` = `1.5.3-experimental`)  
**Common Merge Base**: `011d6b54e42407b2f3a6deaddc47305cf2325a47` (`011d6b5 Merge perf/high-speed: 1.5.3-beta`)  
**Core Directive**: *"Privilege the improvements from the main git (`upstream/main`), then try to improve on it with our high-speed streaming pipeline."*

---

## 1. Git Topology, Remotes & Divergence Audit

### 1.1 Repository & Remote State
| Ref / Remote | Repository / Branch | Commit SHA | Version | Status |
| :--- | :--- | :--- | :--- | :--- |
| `HEAD` (Local) | `perf/phase6-highspeed-streaming` | `15bdb0f` | `1.5.3-experimental` | Clean working tree; 1 commit ahead of `origin/perf/phase6-highspeed-streaming` |
| `origin` | `Madderose/BeamNG.Earth` | `5128a56` (`perf/phase6-highspeed-streaming`) / `d85af06` (`main`) | `1.5.3-experimental` | Latest GitHub release: `v1.5.3-experimental` (Pre-release, `2026-10-20T14:09:38Z`) |
| `upstream` | `TecnaGamer/BeamNG.Earth` | `bd9c764` (`upstream/main`) | `1.5.4-beta` | Tag `v1.5.3-beta` (`011d6b5`) + 45 commits culminating in `1.5.4-beta` |
| Merge Base | `git merge-base HEAD upstream/main` | `011d6b5` | `1.5.3-beta` | Clean divergence point after `v1.5.3-beta` |

### 1.2 Divergent Commit Summary (`011d6b5...upstream/main` vs `011d6b5...HEAD`)

#### Upstream Commits (`> upstream/main`, 45 commits since `011d6b5`):
- **`bd9c764` / `ccbd7b8`**: Release `1.5.4-beta` (`VERSION` bump).
- **`fd6ebff` / `146ebbd`**: **Road surface triangle-cutting along the 2m terrain grid (`roadmesh.follow_ground` + `earthfast.follow_tris`)**: eliminates tires sinking into or floating above crowned/curved terrain between vertices; lowers `DETAIL_ROAD_LIFT` from `0.05m` to `0.025m`.
- **`ca20e61` / `1c446cb`**: **Rural motorway shoulders (`MOTORWAY_RURAL_M = 7.4`, `SHOULDER_M = 2.2`, `edge_margin`)**: adds paved emergency shoulders outside the solid white edge lines on unlit rural motorways and widens `navgraph.driving_width`.
- **`f8fb7d2`**: **Camera-away streaming (`VIEW_AWAY_M = 50.0`, `Conn.view_focus`, `core.viewAway()`)**: when free camera or world map camera moves >50m from the car, visual tiles (`farfield`, `roads`, `veg`, `bldfar`, `update_eye`) stream around both the car and the camera (car first), while physics/collision stays anchored on the car.
- **`07f9574` / `2981197`**: **GitHub #66 Vegetation fixes (`vegetation.py` v13, `trees.lua`)**:
  - Filters false canopy trees on bare salt flats and permanent snow (`BARREN_NEAR_M = 20.0`, Bonneville Salt Flats fix).
  - Restricts bare-ground rocks to sloped terrain (`ROCK_SLOPE = (0.02, 0.10)`, `_slope` from z12 DEM).
  - Caps dense forest tiles at `TILE_ROWS_MAX = 6000` on server and `M.TILE_CAP = {{300, 6000}, {700, 2400}, {1500, 900}, {1e9, 400}}` (`tileThreshold`) in `trees.lua` (fixing Bodø 1.66M items / 394MB Lua heap).
- **`4a74115`**: **GitHub #67 Windows cache file lock resilience (`staging.replace_cached`)**: retries `os.replace` with backoff `(0.02, 0.05, 0.1, 0.25, 0.5)s` when another process or `mmap` holds a cache file open (`PermissionError` WinError 5), keeping the existing valid cache copy if still held.
- **`c2b1ca1`**: **GitHub #27 Session folder recreation (`staging.replace`)**: recreates missing session temp directory with a one-time warning if cleared mid-run.
- **`3b6f76c`**: **GitHub #64 Floating buildings & late bridge decks (`roads.lua`)**: purges `walkQ`, `held`, and `createQ` in `dropTile`, checks `q.tile == tiles[q.key]` before spawning, and checks `playerIn` against the 3D deck box (`DECK_BOX_BELOW_M = 2.2`, `DECK_ON_M = 0.2`) so decks are not held back when the car is driving above them.
- **`bf9013f` / `bd5b6c1` / `1cc6c43`**: **Tunnel portals & shallow underpasses (`roads.py`, `buildings.py`)**: skips service road tunnels (`PORTAL_SKIP_CLASSES = ("service",)`), drops tunnel portals from shallow underpasses (`_shallow_full_low`), extends tunnel bore ends past portals (`_clear_portals`, `PORTAL_BORE_CLEAR_M = 2.0`), and caps bridge deck approach crests (`_ground_envelope`, `DECK_CREST_R = 60.0`, `DECK_ROAD_CLEAR = 7.5`).
- **`7e04156`**: **GitHub #55 Narrow median self-folding fix (`sidewalks.py`)**: clamps ramp run `rr` and landing `xp` on narrow islands (`w < RAMP_RUN`).
- **`ec054dc` / `fc05c64` / `32a78e9` / `a057b65` / `fa076be` / `09fb070` / `2e62ab7`**: **Level Select, World Map, Places, Previews & Controller Polish**:
  - `levelinfo.lua`, `places.lua`, `placepreview.py`, `randomplace.py`, `prewarm.py`.
  - Default spawn on Whitney Portal Road (`36.5869, -118.1325`, `1805m`), 12 curated starter places (including Pécs `46.0707, 18.2331`), random driveable place button, satellite thumbnails on level select cards.
  - Full controller navigation on World Map (`BigMap` action map, left/right stick pan/cursor, LT/RT zoom, X/Y bindings, `keepMapMenuActions`).
- **`639741f` / `6bc5932` / `fc87639` / `a25ce2f` / `6a90df9` / `9713163` / `1ff8035` / `a84e798`**: **Server & Memory Performance (`budget.py`, `pacer.py`, `sampler.py`, `dem.py`, `mapdata.py`, `streetwidth.py`, `seafloor.py`, `gravity.py`, `earthd.py`, `lib.rs`)**:
  - Memory-mapped `.npy` mirrors (`np.memmap`, `mode="r"`) for DEM, mapdata, streetwidths, seafloors, and EGM2008 gravity so worker processes share physical pages without per-process RAM duplication.
  - `budget.HOST_RAM_MB` auto-scales cache sizes to host RAM (`--memory-profile low|auto|high`).
  - `pacer.py` yields background warm threads while the first block after a teleport is building.
  - `earthd.py` offloads `navgraph`, detail `base_photo`, and plain `far_tile` builds into worker pools.
  - `lib.rs` (`VERSION = 34`) gates `py.allow_threads` behind `RELEASE_MIN = 200_000` work items (`fn release`) to avoid 5ms Linux/Steam Deck GIL re-acquisition stalls on micro-calls, and adds `measure_row32`, `terrain_at`, and `follow_tris`.
  - Merges our PR #41 (`cb4f696`, `framing.lua` $O(1)$ read-head offset).

#### Local Commits (`< HEAD`, 6 commits since `011d6b5`):
- **`368356b` / `02ab667` / `0326939` / `fb42ca1` / `5128a56` / `15bdb0f`**:
  - **Phase 4–8 High-Speed Streaming Pipeline (`80–200+ mph` zero-stutter architecture)**:
    - Velocity-vector lookahead capsule (`lead`, `farfield.seg_distance`) in `earthd.py` & `farfield.py`.
    - Algebraic swap-group cancellation (`waitingInsts`, `g.insts`, `g.needs`) and speed-gated C1 instant swaps (`spd >= 50 m/s` or `nearest <= INSTANT_M`) in `farfield.lua` & `crossover.lua`.
    - Multi-process `road_pool` list with per-process `warm_qs` in `earthd.py`.
    - Predictive D3D12 swapchain governor (`emaEngineMs`, `tickBase` idle C++ Ticking subtraction, `ENGINE_MAX_DEBT_MS = 8.0`, `URGENT_TARGET_MS = 6.0`, `DELETE_BUDGET_MS = 0.5`) in `governor.lua`.
    - Governed tree micro-chunking (`PER_FRAME = 20`, `MAX_WALL_MS = 0.85`, `MAX_RING_M = 900`, `SOLID_M = 90`, `SHAPE_VARIANTS = 1`, zero-allocation `scratchMat`/`scratchEuler`/`scratchPos`, compact 16-byte `.vbin` sideband encoding) in `trees.lua` & `vegetation.py`.
    - Two-lane IPC framing (`LANE0_TYPES` immediate control vs time-sliced Lane 1 data under `0.5 ms/frame`), adaptive pose cadence (`0.20s` at >25 m/s), heavy-frame subsystem isolation, incremental Lua GC (`collectgarbage('step', 30)`), and velocity-adaptive SDSM shadow scaling in `core.lua`.
    - Material & TSStatic shadow cascade culling (`castShadows = 0` on glass, wires, road surfaces, far tiles, and distant forest rings >220m; single-primitive `lite=True` coarse buildings) in `buildings.py`, `roads.lua`, `farfield.lua`, `trees.lua`, `buildings.materials.json`, `main.materials.json`.
    - $256 \times 256$ physics micro-block in `mesh` mode (`follow.lua`, `terrain.lua`, `earthd.py`) + skipped `.png` layer mask writes on `.ter` swaps (`TER_SWAP`).
    - Generational ping-pong `.cdae` slots (`slot_<n>_0.cdae` / `slot_<n>_1.cdae`) + external staging (`staging.master_for` / `stage_for`) in `matslots.py` & `staging.py`.
    - Travel-distance & structure-urgency gated `be:reloadCollision()` in `roads.lua`.
    - One-time route registration latch (`M.ensureRoutes()`) in `settings.lua`.
    - Sidewalk ground conformance (`_conform_walks`, `dz`, `SKIRT = 1.2`) in `roads.py` & `sidewalks.py`.
    - Parallel test runner (`tools/parallel_tests.py -j 12`).

---

## 2. Complete 3-Way Divergence & Conflict Matrix

Running `git merge-tree --write-tree HEAD upstream/main` identifies **134 changed files** across both branches since `011d6b5`:
- **34 files modified on BOTH sides**:
  - **14 Hard Content Conflicts** (require manual 3-way resolution).
  - **20 Auto-Merged Overlapping Files** (require semantic verification to prevent silent contract mismatches).
- **43 files modified ONLY on `upstream/main`** (clean fast-forward adoption).
- **57 files modified/added ONLY on `HEAD`** (preserved local high-speed pipeline modules, tests, benchmarks, and tools).

### 2.1 The 14 Hard-Conflict Files
| # | File Path | Upstream (`1.5.4-beta`) Changes | Local (`HEAD`) High-Speed Changes | Harmonization Resolution Strategy |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `VERSION` | `1.5.4-beta` | `1.5.3-experimental` | Set to **`1.5.4-experimental`** (per `AGENTS.md` to avoid colliding with upstream `1.5.4-beta` or our `v1.5.3-experimental`). |
| 2 | `server/earthd.py` | `DETAIL_ROAD_LIFT=0.025`, `VIEW_AWAY_M=50` (`view_focus`), `road_pool` navgraph offload, `base_pool`, `far_pool`, `hm_here`, `q=anchor_q` in `roadmesh.build`, `prewarm`, `random_place`, `place_previews`, `budget`/`pacer`/`sampler`/`tracemalloc`. | Multi-worker `road_pool` list + `warm_qs`, velocity capsule (`lead`) in `reselect_far`/`order_far`, driving-throttled `_delete_batch`, `TCP_NODELAY`, `_inline_tile_meta`, L0/L1 graded far tiles, `TER_SWAP` mask skip, 256px mesh block clamp. | Adopt upstream `1.5.4-beta` structure as base; wrap multi-worker `road_pool` list with `_pick_road_pool()` so both `build_roads_tile` and `build_navgraph` round-robin cleanly; layer velocity capsule onto `*self.view_focus`; preserve `_delete_batch`, `_inline_tile_meta`, `TER_SWAP`, and L0/L1 graded far tiles. |
| 3 | `server/roads.py` | Rural motorways (`MOTORWAY_RURAL_M=7.4`, `SHOULDER_M=2.2`, `edge_margin`), tunnel portals (`_clear_portals`, `_road_caps`, `_shallow_full_low`), deck envelope (`_ground_envelope`, `DECK_ROAD_CLEAR=7.5`), `simplify(ztol)`, `feats.boxes(frame)` fast skip, `Tracker.empty`/`retry`, `view=None` in `on_pose`, `chunks: []` when `road_mesh` built. | `BUILD_PER_POSE = 8`, `_conform_walks` (`WALK_STEP = 4.0`, `back_z` ground conformance), `sidewalk_stop` outer-edge alignment when crossing road has no sidewalks. | Adopt upstream `1.5.4-beta` `roads.py` in full; layer `BUILD_PER_POSE = 8`, `_conform_walks` (passing `back_z` to `b.add_run`), and the 3-line `sidewalk_stop` outer-edge fallback on top. |
| 4 | `server/sidewalks.py` | GitHub #55 narrow median clamp (`rr`, `xp`), `np.concatenate` replacing `np.r_`. | `dz=0.0` parameter (`dz_slab` ground conformance) + 9th profile vertex (`SKIRT = 1.2`, `LEAN = (0,2,5,6,7,8)`). | Combine upstream's narrow-median `rr` and `xp` formulas with `dz_slab = min(0.0, float(dz))` and our 9-vertex `SKIRT` profile. |
| 5 | `server/staging.py` | GitHub #27 `_remade` warning log in `replace()`, GitHub #67 `replace_cached()` with `REPLACE_WAITS` retry loop for Windows `PermissionError`. | `mark_temporary` (`FILE_ATTRIBUTE_TEMPORARY`), `session_dir`, `master_for`, `stage_for` (external staging outside watched user folder). | Preserve all local external staging helpers (`mark_temporary`, `session_dir`, `master_for`, `stage_for`) AND integrate upstream's `_remade` warning into `replace()` plus upstream's `replace_cached()` function. |
| 6 | `server/dem.py` | `staging.replace_cached(tmp, path)` + decoded `.npy` `np.memmap` mirror (`_mirror_get`, `_mirror_put`, `_mirror_prune`, `MIRROR_MB=1024`). | Single-line `staging.replace(tmp, path)`. | Adopt upstream `1.5.4-beta` `server/dem.py` 100%. |
| 7 | `server/heightmap.py` | `staging.replace(tmp, path)` with `import staging` at top of module. | `staging.replace(tmp, path)` with local `import staging` inside `write_png`. | Adopt upstream `1.5.4-beta` `server/heightmap.py` 100%. |
| 8 | `server/surface.py` | `staging.replace(tmp, path)` for masks and `.ter`. | `write_masks=True` parameter on `build()` to skip writing 10 `_m0.._m9.png` masks when `.ter` swap is used (`cx != 0 or cy != 0`), plus `staging.replace`. | Adopt upstream `surface.py` and retain the `write_masks=True` parameter in `build()`. |
| 9 | `server/vegetation.py` | `VERSION = 13`, `BARREN_NEAR_M = 20.0` (GH #66 salt flats/snow), `ROCK_SLOPE` + `_slope` (playas), `TILE_ROWS_MAX = 6000` (Bodø), `pacer.hold()`, `staging.replace_cached`, `Tracker.on_pose(..., view=None)`. | `.vbin` 16-byte binary tree packing (`pack_vbin`, `write_vbin`, `send_tile`, `out.vbin` on `JsonRows`). | Adopt upstream `1.5.4-beta` `vegetation.py` as base (`VERSION=13`, `BARREN_NEAR_M`, `ROCK_SLOPE`, `TILE_ROWS_MAX=6000`, `view=None`), and layer `.vbin` packing (`pack_vbin`, `write_vbin`, `send_tile`) on top. |
| 10 | `native/earthfast/src/lib.rs` | `VERSION = 34`, `RELEASE_MIN = 200_000` (`fn release`), `wall_ray<T>`, `measure_row32`, `terrain_at`, `follow_tris`. | Empty/bounds safety guards (`n == 0`, `ncols() < 2`, `step > 0.0`, `saturating_sub`) + `allow_threads`. | Adopt upstream `VERSION = 34` with `release(py, work, ...)`, `measure_row32`, `terrain_at`, and `follow_tris`, keeping our zero-length/bounds guards inside each kernel. Keep upstream's compiled `server/earthfast.pyd` & `server/earthfast.abi3.so` (v34). |
| 11 | `mod/.../core.lua` | `levelinfo`, `places`, `rebase.couplings()` (trailer re-hitching), `startTeleport` (saved/random places), `roads.prewarm`, `place_previews_ready`, `random_place_result`, `M.viewAway()`, early return when `not st.inOurLevel`, `groundcover.enginePatch`, `onFilesChanged` for `places.FILE`. | Two-lane IPC (`lane0Q`/`lane1Q`, `0.5ms` budget), adaptive `poseInterval` (`0.20s`), `gov:setUrgent`, `gov:chargeEngine`, `heavyFrame` isolation, incremental Lua GC (`collectgarbage('step', 30)`), SDSM shadow scaling in `onPreRender`, `hookFileWatchers` filter. | Adopt upstream `core.lua` features in full; layer Two-Lane IPC (adding `random_place_result` and `place_previews_ready` to `LANE0_TYPES`), adaptive pose cadence, governor/GC/shadow hooks, and update `hookFileWatchers` so `places.FILE` changes pass through to `M.onFilesChanged`. |
| 12 | `mod/.../roads.lua` | `SIDE_PENALTY=4`, `LEAD_MAX_M=2000`, `unitStats`/`noteUnit`, `dropTile` purge of `walkQ`/`held`/`createQ` (GH #64), `q.tile == tiles[q.key]`, `playerIn` 3D deck surface check, `viewAt` + path priority in `nextWalk`, `M.prewarm`, `gov:chargeMotion(ms)`. | Generational `slotOf` regex (`/slot_(%d+)[_%d]*%.cdae$`), shadow culling (`castShadows=0` except `bld` & `deck`), inlined `bldfar_tile` metadata fast-path, travel-distance & structure-urgency gated `reloadCollision`. | Adopt upstream `roads.lua` in full; layer generational `slotOf`, shadow culling in `createWalk`/`spawnWalk`/`spawnFar`, inlined `onFarTile` metadata, and travel-distance/urgency collision reload gating. |
| 13 | `mod/.../trees.lua` | `M.TILE_CAP` + `tileThreshold(d, t)` (GH #66), `M.update(anchorId, player, view)` camera-away support (`dCar` for solid collision vs `view` for visual rings). | Governed micro-chunking (`PER_FRAME=20`, `MAX_WALL_MS=0.85`, `MAX_RING_M=900`, `SOLID_M=90`, `SHAPE_VARIANTS=1`), zero-alloc `makeItem`, `.vbin` `onBin`/`decodeBinRow`, collision debounce, `M.update(anchorId, player, gov)`. | Unify signature to `M.update(anchorId, player, view, gov)` (with duck-typed fallback if 3rd arg `view` is a `gov` table); integrate `M.TILE_CAP` / `tileThreshold(d, t)` with support for both `t.rows` and binary `t.bin`; use `dView` (`o[2]`) for visual rings/shadow culling and `dCar` (`o[3]`) for `near` solid collision. |
| 14 | `server/tests/test_staging.py` | `test_session_folder_deleted_mid_run` (GH #27) and `test_cache_file_held_elsewhere` (GH #67). | `test_master_for_stages_per_session_outside_user_folder`. | Keep all 3 test methods in `StagingTest`. |

---

## 3. Detailed File-by-File Merge Harmonization Analysis

### 3.1 `server/earthd.py`
- **Upstream (`1.5.4-beta`) Base Architecture**:
  - Imports `budget`, `pacer`, `placepreview`, `prewarm`, `randomplace`, `sampler`, and optional `tracemalloc` (`BNGE_TRACEMALLOC`).
  - Lowers `DETAIL_ROAD_LIFT` from `0.05` to `0.025` (paired with `roadmesh.FOLLOW_TOL = 0.02`).
  - Adds `VIEW_AWAY_M = 50.0`, `Connection.camera_away(cam)`, and `Connection.view_focus` so visual streaming follows free-camera / world-map views while physics stays at `self.focus`.
  - Offloads `build_navgraph` to `self.road_pool` via `blockworker.navgraph`.
  - Offloads detail-mode `base_photo` to `self.base_pool` (the opposite lane's block worker process) and plain `far_tile` builds (`deshadow` and `colormatch` off) to `self.far_pool` (`blockworker.far_tile`).
  - Passes `q=self.anchor_q(anchor)` into `blockworker.roads_tile` and `roadmesh.build(..., clip=box, follow=True, q=..., drawn=drawn)`.
  - Replaces `self.hm_inflight` with `self.hm_here` (throttling tile workers only when a block builds in-process) and throttles imagery prefetch per tile with `self.prefetched` (`PREFETCH_AGAIN_S = 2.0`).
  - Adds `prewarm` shape path to `hello`, and handles `random_place` and `place_previews` client messages.
- **High-Speed Streaming Layer Integration**:
  1. **Multi-Worker `road_pool` & `warm_qs` Harmonization**:
     - Keep `self.road_pool` as a list of `n_road_procs` single-worker `ProcessPoolExecutor`s (each initialized with its own `multiprocessing.Queue` in `self.warm_qs` so warm cell keys broadcast to every road worker).
     - Add helper method `Server._pick_road_pool(self)`:
       ```python
       def _pick_road_pool(self):
           if not self.road_pool:
               return None
           if isinstance(self.road_pool, list):
               pool = self.road_pool[self._road_rr % len(self.road_pool)]
               self._road_rr += 1
               return pool
           return self.road_pool
       ```
     - Use `pool = self._pick_road_pool()` in **both** `build_roads_tile` and upstream's `build_navgraph`! Also update `far_bld_pool` initialization and `Server.close()` to iterate over `self.road_pool` when it is a list.
  2. **Velocity-Vector Lookahead Capsule (`lead`) + Camera-Away (`view_focus`)**:
     - In `Connection.reselect_far`: compute `lead = None` and `dyn_radii = self.s.near_radii`. When `self.view_at is None` (camera is with the car, not in free-cam/map view) and `self.speed > 2.0`, compute `t_look = min(7.0, self.speed * 0.12)`, `lead_d = min(350.0, self.speed * t_look)`, `lead = (fx + self.vx * scale, fy + self.vy * scale)`, and tighten lateral radii `dyn_radii = (min(r0, 160.0), min(r1, 380.0), ...)`. Pass `lead=lead` into `farfield.select(*self.view_focus, ..., near_radii=dyn_radii, lead=lead)`.
     - In `Connection.order_far`: use `self.view_focus` as `(fx, fy)`, compute `lead_pt` when `self.view_at is None and self.speed > 2.0`, evaluate `d = farfield.seg_distance(k, fx, fy, lead_pt[0], lead_pt[1])`, and apply cosine directional priority inside class `0` (`lvl <= 0 and d <= 380.0`).
  3. **Graded Far Tiles (`lvl <= 1`), `TER_SWAP` Mask Skipping & 256px Mesh Block**:
     - In `Server.build_far_tile`: preserve `use_graded = (lvl <= 1)` with `far_lift = gradingmod.ROAD_LIFT if lvl <= 0 else gradingmod.ROAD_LIFT * 0.5`. Note: only offload a tile to `self.far_pool` (`blockworker.far_tile`) when `not (use_graded and self.roads_on and self.mapdata is not None)` (or pass road grading context), so L-2..L1 tiles near the player always receive road grading!
     - Preserve `TER_SWAP` check (`use_ter = TER_SWAP and (cx != 0 or cy != 0)`, `write_masks=not use_ter`) and the 256px physics block clamp when `near_visual == "mesh"`.
  4. **Driving-Aware Batch File Deletion (`_delete_batch`) & Inlined `bldfar_tile` Metadata (`_inline_tile_meta`)**:
     - Preserve `DELETE_DRIVE_INTERVAL = 3.0` (`_delete_batch` deleting up to 8 files when `speed > 5.0`), `TCP_NODELAY`, and `_inline_tile_meta` in `Connection.send`.

### 3.2 `server/roads.py` & `server/roadmesh.py`
- **Upstream (`1.5.4-beta`) Base**:
  - `server/roadmesh.py` has zero local changes since `011d6b5`; adopt upstream `1.5.4-beta` 100% (`follow_ground`, `_clip_tris`, `_reach_past`, `_height_grid`, `FOLLOW_TOL = 0.02`, `FOLLOW_MAX_CELL = 16.0`).
  - `server/roads.py`: adopt upstream's rural motorways (`MOTORWAY_RURAL_M`, `SHOULDER_M`, `edge_margin`), tunnel portal clearance (`_clear_portals`, `_road_caps`, `_shallow_full_low`), bridge deck envelope (`_ground_envelope`, `DECK_CREST_R = 60.0`, `DECK_ROAD_CLEAR = 7.5`), `simplify(..., ztol=SIMPLIFY_Z_M)`, `feats.boxes(frame)` fast skip, `Tracker.empty`/`retry`, and `view=None` camera-away support in `Tracker.on_pose`.
- **High-Speed Streaming Layer Integration**:
  - Set `BUILD_PER_POSE = 8`.
  - Keep `WALK_STEP = 4.0` and `_conform_walks(walks, line, width, elev)` in `build_tile`, passing `back_z=item[3]` into `b.add_run(pts, spec.curb, spec.sidewalk, drops, back_z=back_z)`.
  - Keep the 3-line `sidewalk_stop` outer-edge alignment when the crossing road has `other.sidewalk <= 0`.

### 3.3 `server/sidewalks.py`
- **Upstream (`1.5.4-beta`) Base**:
  - Clamps `rr = max(CURB_W + NARROW_EDGE_M, min(RAMP_RUN, w - NARROW_EDGE_M))` and `xp = CURB_W + min(PAD_W, (rr - CURB_W) / 2)` so narrow medians (`w < RAMP_RUN`) never fold back over themselves (GitHub #55), and uses `np.concatenate` instead of `np.r_`.
- **High-Speed / Phase 4 Layer Integration**:
  - Retain `SKIRT = 1.2`, `LEAN = (0, 2, 5, 6, 7, 8)`, and `dz=0.0` parameter on `_profile(w, h, drop=0.0, dz=0.0)`, computing:
    ```python
    rr = max(CURB_W + NARROW_EDGE_M, min(RAMP_RUN, w - NARROW_EDGE_M))
    xp = CURB_W + min(PAD_W, (rr - CURB_W) / 2)
    dz_slab = min(0.0, float(dz))
    span = max(w - CURB_W, 1e-6)
    zr = h + rr * CROSS_SLOPE + dz_slab * min(1.0, max(0.0, rr - CURB_W) / span)
    zp = hr + (zr - hr) * (xp - CURB_W) / max(rr - CURB_W, 1e-6)
    ```
    and the 9th skirt vertex `[w_back, back_bot - SKIRT]`.

### 3.4 `server/staging.py`, `server/dem.py`, `server/surface.py`, `server/heightmap.py`, `server/matslots.py`
- **`server/staging.py`**:
  - Combine our external staging architecture (`STAGING = "beamngEarth-staging"`, `mark_temporary`, `session_dir`, `master_for`, `stage_for`) with upstream's `_remade` warning log inside `replace(tmp, path)` (GitHub #27) and upstream's `replace_cached(tmp, path)` retry loop (`REPLACE_WAITS = (0.02, 0.05, 0.1, 0.25, 0.5)`, GitHub #67).
  - Ensure `replace(tmp, path)` also calls `mark_temporary(tmp)` before `os.replace(tmp, path)` when recreating a missing directory.
- **`server/dem.py` & `server/heightmap.py`**:
  - Adopt upstream `1.5.4-beta` 100% (`dem.py` uses `staging.replace_cached` and `.npy` `np.memmap` mirrors; `heightmap.py` uses `staging.replace`).
- **`server/surface.py`**:
  - Adopt upstream `1.5.4-beta` and preserve the optional `write_masks=True` argument on `build()`.
- **`server/matslots.py`**:
  - Auto-merges cleanly: keeps our generational ping-pong slot naming (`slot_<n>_<gen>.cdae`, `_SlotFileMethod`, `self.gen`) and `staging.master_for(slot_path)` alongside upstream's `staging.replace`.

### 3.5 `server/buildings.py` & `buildings.materials.json`
- **Auto-Merge Verification**:
  - Upstream optimizes `Mesh` to flat coordinate lists (`v`, `n`, `uv`, `tris`), converts `triangulate`/`oriented_box` to plain Python floats, caches `_three_d` and `line_boxes` on `Features`, skips `PORTAL_SKIP_CLASSES = ("service",)` tunnels (GitHub #60), filters ML vehicle footprints on roads (`_ml_false`), and batches building ground heights into one `elev(lats, lons)` call.
  - Our changes add `GLASS = "bne_bld_glass"` (`castShadows: false` in `buildings.materials.json`), single-primitive `lite=True` merging (`build_parts`, `far_tile`), `FOUNDATION_M = 3.0`, hillside `base_z = min(gmax, gmin + 1.5)`, and roof ridge rise caps (`6.5m` church / `4.2m` house).
  - **Semantic Check**: Verify `_walls` in `buildings.py` uses upstream's plain-float `pts` loop and `whole=lite` while routing window quads to `GLASS` when `not lite`.

### 3.6 `server/vegetation.py` & `mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua`
- **`server/vegetation.py`**:
  - Adopt upstream `VERSION = 13`, `BARREN_NEAR_M = 20.0`, `ROCK_SLOPE = (0.02, 0.10)`, `_slope(px, py)`, `TILE_ROWS_MAX = 6000`, `pacer.hold()`, `staging.replace_cached`, and `Tracker.on_pose(..., view=None)`.
  - Layer our `.vbin` 16-byte binary packing (`VBIN_STRUCT`, `VBIN_STRIDE = 16`, `_pack_vbin_arrays`, `pack_vbin`, `write_vbin`, `send_tile`) on top.
  - In `write_tile`: write `.vbin` both when `rows` is a `list`/`tuple` AND when `isinstance(rows, JsonRows)` (using `getattr(rows, "vbin", None)`), so `veg_tile` always has a `.vbin` sideband ready.
- **`mod/.../trees.lua`**:
  - **Signature Harmonization**: Define `function M.update(anchorId, player, view, gov)`. Add a duck-typing guard at the top of `M.update`:
    ```lua
    if type(view) == 'table' and (view.try ~= nil or view.tokens ~= nil or view.frame ~= nil) and gov == nil then
      gov, view = view, nil
    end
    ```
    so callers passing `(anchorId, player, gov)` (our Phase 7/8 tests) and callers passing `(anchorId, player, view)` (upstream `1.5.4-beta` tests) or `(anchorId, player, view, gov)` (`core.lua`) all work identically!
  - **Dense Tile Capping (`M.TILE_CAP` + `tileThreshold`)**: Include upstream's `M.TILE_CAP = { { 300, 6000 }, { 700, 2400 }, { 1500, 900 }, { 1e9, 400 } }` and `tileThreshold(d, t)`. Enhance `tileThreshold(d, t)` to read row count and ranks from either `t.rows` OR binary `t.bin` (`decodeBinRow(t.bin, i)[8]`).
  - **Camera-Away (`view`) + Velocity Corridor Priority**: Compute `dCar = boxDist(player, t)` and `dView = view and math.min(boxDist(view, t), dCar) or dCar`. Use `dView` for `want = tileThreshold(dView, t)`, `band = groupBand(t, dView)`, and `shadow = dView <= shadowMaxM`, while using `dCar` for `near` (colliding solid trees around the car).

### 3.7 `native/earthfast/src/lib.rs`
- **Upstream (`1.5.4-beta`) Base**:
  - `VERSION = 34`, `RELEASE_MIN = 200_000`, `fn release(py, work, f)`, generic `wall_ray<T>`, `measure_row32`, `terrain_at`, and `follow_tris`.
- **High-Speed Layer Integration**:
  - Keep upstream's `VERSION = 34` and all new functions (`measure_row32`, `terrain_at`, `follow_tris`, `release`).
  - Preserve our zero-length / degenerate input guards (`if n == 0`, `if p.ncols() < 2`, `step > 0.0`, `saturating_sub`) inside the kernel bodies while using upstream's work-gated `release(py, work, || ...)` instead of unconditional `py.allow_threads`.
  - Retain upstream's precompiled `server/earthfast.pyd` and `server/earthfast.abi3.so` (which export `VERSION = 34`, `measure_row32`, `terrain_at`, and `follow_tris`).

### 3.8 `mod/.../core.lua`, `mod/.../roads.lua`, `mod/.../farfield.lua`, `mod/.../governor.lua`, `mod/.../settings.lua`
- **`mod/.../core.lua`**:
  - Adopt upstream `levelinfo`, `places`, `rebase.couplings()`, `startTeleport()`, `roads.prewarm(msg.prewarm)`, `place_previews_ready`, `random_place_result`, `M.viewAway()`, early exit in `onUpdate` when `not st.inOurLevel and not st.active`, `groundcover.enginePatch(st.inOurLevel)`, and `M.onFilesChanged` for `places.FILE`.
  - Layer Two-Lane IPC (`lane0Q`/`lane1Q`), adding `random_place_result = true` and `place_previews_ready = true` to `LANE0_TYPES` so UI/teleport responses dispatch with zero latency.
  - In `hookFileWatchers`: check if any file entry matches `places.FILE` and invoke `M.onFilesChanged` (or let non-`/temp/beamngEarth/` files pass through, which `filterEarthTempFiles` already does since `places.FILE` is `/settings/beamngEarth/places.json`!).
  - In `onUpdate`: pass `M.viewAway()` AND `gov` to `trees.update(st.anchorId, st.player, M.viewAway(), gov)` and `roads.update(gov, st.anchorId, st.player, M.viewAway())` inside the `not heavyFrame` guard, followed by `collectgarbage('step', 30)`.
- **`mod/.../roads.lua`**:
  - Adopt upstream `SIDE_PENALTY = 4`, `LEAD_MAX_M = 2000`, `unitStats`/`noteUnit`, `dropTile` purge of `walkQ`/`held`/`createQ` (setting `q.tile = tiles[key]` on every `walkQ` entry), `playerIn` 3D deck surface check (`DECK_BOX_BELOW_M = 2.2`, `DECK_ON_M = 0.2`), `viewAt` + path priority in `M.nextWalk`, `M.prewarm(path)`, and `gov:chargeMotion(ms)` on collision reload.
  - Layer our generational `slotOf` regex (`/slot_(%d+)[_%d]*%.cdae$`), shadow culling (`castShadows = 0` on non-`bld`/non-`deck` meshes), inlined `bldfar_tile` metadata in `M.onFarTile`, and travel-distance/urgency gated collision reloads (`RELOAD_HORIZON_RATIO = 0.55`, `RELOAD_DRIVE_MAX_S = 15.0`, `hasUrgentStructure`).
- **`mod/.../farfield.lua`, `mod/.../governor.lua`, `mod/.../follow.lua`, `mod/.../terrain.lua`, `mod/.../crossover.lua`, `mod/.../dev.lua`, `mod/.../satmat.lua`**:
  - Upstream did **not** modify these 7 Lua files after `011d6b5`! All our Phase 4–8 high-speed streaming optimizations in these files merge cleanly with zero upstream conflicts.
- **`mod/.../settings.lua` & `mod/.../EarthMap.vue`**:
  - Auto-merged cleanly! `settings.lua` combines upstream's controller navigation (`M.mapControls`, `M.mapBlockedActions`, `BigMap` action map, `keepMapMenuActions`) with our one-time route registration latch `M.ensureRoutes()`. `EarthMap.vue` combines upstream's controller cursor/hints and saved-location star button with our route polyline simplification (`simplify_pts=False`).

---

## 4. Top 10 Conflict Traps & Mandatory Safeguards

1. **Trap 1 — `self.road_pool` List vs Single Executor in `Server.build_navgraph` (`server/earthd.py`)**:
   - *Hazard*: Upstream's new `build_navgraph` calls `self.road_pool.submit(blockworker.navgraph, ...)`, assuming `self.road_pool` is a single `ProcessPoolExecutor`. In our branch, `self.road_pool` is a `list` of single-worker executors (one per `warm_q`). Calling `.submit()` on a `list` raises `AttributeError: 'list' object has no attribute 'submit'`.
   - *Resolution*: Route both `build_roads_tile` and `build_navgraph` through `self._pick_road_pool()`.
2. **Trap 2 — `trees.update` 3rd Argument Collision (`view` vs `gov`) (`trees.lua`, `core.lua`)**:
   - *Hazard*: Upstream changed `trees.update(anchorId, player)` to `trees.update(anchorId, player, view)` where `view` is `{x, y}` camera coordinates. Our branch changed it to `trees.update(anchorId, player, gov)` where `gov` is the Governor table.
   - *Resolution*: Use 4-parameter `M.update(anchorId, player, view, gov)` in `trees.lua` and `core.lua`, and duck-type `view` inside `trees.update` (`if type(view) == 'table' and (view.try ~= nil or view.tokens ~= nil or view.frame ~= nil) and gov == nil then gov, view = view, nil end`).
3. **Trap 3 — `walkQ` Entry Missing `tile = tiles[key]` in `roads.lua`**:
   - *Hazard*: Upstream's GitHub #64 fix in `roads.lua` checks `if q.tile ~= tiles[q.key] then goto next end` inside `M.nextWalk`. If our `table.insert(walkQ, ...)` for `road` omits `tile = tiles[key]`, `q.tile` is `nil ~= tiles[q.key]` and **every road surface mesh would be silently skipped!**
   - *Resolution*: Ensure every `walkQ` entry includes `tile = tiles[key]`.
4. **Trap 4 — `M.TILE_CAP` / `tileThreshold` With Binary `.vbin` Tiles (`trees.lua`)**:
   - *Hazard*: Upstream's `tileThreshold(d, t)` indexes `t.rows` (`#rows <= r[2]` and `for i, row in ipairs(rows) do rk[i] = row[8]`). When `.vbin` binary streaming is active, `t.rows` is `nil` and `t.bin` holds the 16-byte records (`t.nRows`).
   - *Resolution*: In `tileThreshold(d, t)`, compute row count as `local nRows = t.bin and t.nRows or (t.rows and #t.rows or 0)` and extract ranks from either `t.rows` or `decodeBinRow(t.bin, i)[8]`.
5. **Trap 5 — Graded L0/L1 Far Tiles Bypassed by `self.far_pool` (`server/earthd.py`)**:
   - *Hazard*: Upstream offloads plain `far_tile` builds (when `deshadow` and `colormatch` are off) to `self.far_pool` (`blockworker.far_tile`), which does not run `grader_for(anchor)`. If L-2..L1 tiles are sent to `far_pool`, road grading on near farfield tiles is bypassed, re-introducing mountain road pokethrough.
   - *Resolution*: Only offload to `self.far_pool` when `lvl > 1` (or when `not (use_graded and self.roads_on and self.mapdata is not None)`).
6. **Trap 6 — Velocity Lookahead Capsule During Free-Camera / World-Map Panning (`server/earthd.py`)**:
   - *Hazard*: Applying car velocity lookahead `(self.vx, self.vy)` to `self.view_focus` when the user is panning the world map or free camera >50m away (`self.view_at is not None`) skews camera-centered tile selection.
   - *Resolution*: Only apply velocity capsule `lead` and tightened `dyn_radii` when `self.view_at is None` (camera is near the car).
7. **Trap 7 — `earthfast` Binary Version 34 & New Symbols (`lib.rs`, `earthfast.pyd`)**:
   - *Hazard*: Upstream bumped `native/earthfast/src/lib.rs` `VERSION` from `33` to `34` and added `measure_row32`, `terrain_at`, and `follow_tris`. `test_fast.py` asserts `fast._ef.VERSION == 34`, and `roadmesh.py` / `streetwidth.py` call `follow_tris` / `measure_row32`.
   - *Resolution*: Keep upstream's compiled `server/earthfast.pyd` and `server/earthfast.abi3.so` (v34) or recompile `earthfast` from the harmonized `lib.rs` at `VERSION = 34`.
8. **Trap 8 — `staging.replace` vs `staging.replace_cached` (`server/staging.py`, `server/tests/test_staging.py`)**:
   - *Hazard*: Upstream's `dem.py`, `imagery.py`, `mapdata.py`, `seafloor.py`, `streetwidth.py`, and `vegetation.py` call `staging.replace_cached(tmp, path)`. Omitting `replace_cached` or `REPLACE_WAITS` breaks all cache writes and `test_staging.py`.
   - *Resolution*: Include both `replace` (with `_remade` warning + `mark_temporary`) and `replace_cached` (with `REPLACE_WAITS`) in `server/staging.py`.
9. **Trap 9 — Protocol Schema Agreement (`server/tests/test_protocol_agreement.py`)**:
   - *Hazard*: `test_protocol_agreement.py` parses `core.lua` and `places.lua` for `net.send({...})` and validates all server-to-mod messages.
   - *Resolution*: Union upstream's new message schemas (`random_place`, `place_previews`, `random_place_result`, `place_previews_ready`, `hello.prewarm`, `places.lua` scan in `mod_sends()`) with our high-speed optional fields (`veg_tile.vbin_path`/`bin`, `bldfar_tile.shape`/`pos`/`rot`/`scale`, generational `SHAPE_RE`, `matslots.file()` check, and active-anchor filter `m.get("anchorId") == b["anchorId"]`).
10. **Trap 10 — `LANE0_TYPES` Missing New UI Messages in `core.lua`**:
    - *Hazard*: If `random_place_result` or `place_previews_ready` are routed to `lane1Q`, level-select UI callbacks could wait behind tile messages if a session is active.
    - *Resolution*: Add `random_place_result = true` and `place_previews_ready = true` to `LANE0_TYPES` in `core.lua`.

---

## 5. Test & Validation Strategy

### 5.1 Automated Test Suite Execution Plan
Per `AGENTS.md`, all harmonization changes must be validated using the parallel test runner across 12 workers:
```powershell
python tools/parallel_tests.py -j 12
```
This executes all **35 Python + Lua test suites** (including upstream's new `test_budget.py`, `test_pacer.py`, `test_placepreview.py`, `test_prewarm.py`, `test_randomplace.py`, `test_sampler.py`, and `mod/tests/test_places.lua`):
1. **Targeted Conflict Verification First**:
   ```powershell
   python -m unittest server/tests/test_staging.py server/tests/test_sidewalk_collision.py server/tests/test_roadmesh.py server/tests/test_roads.py server/tests/test_buildings.py server/tests/test_vegetation.py server/tests/test_matslots.py server/tests/test_fast.py
   ```
2. **Protocol & Mod Simulation Verification**:
   ```powershell
   python -m unittest server/tests/test_modsim.py server/tests/test_protocol_agreement.py server/tests/test_server.py
   ```
3. **Full Parallel Suite Sign-Off**:
   ```powershell
   python tools/parallel_tests.py -j 12
   ```

### 5.2 Versioning & Release Strategy (Compliance with `AGENTS.md`)
- **Current Version Audit**:
  - Local `VERSION`: `1.5.3-experimental`
  - Upstream `VERSION`: `1.5.4-beta`
  - Existing release on `Madderose/BeamNG.Earth`: `v1.5.3-experimental` (`2026-10-20T14:09:38Z`)
  - Upstream tags: `v1.5.3-beta` (`011d6b5`), `v1.5.2-beta` (`c703230`), etc.
- **Selected Target Version**: **`1.5.4-experimental`** (or `1.5.4-preview`).
- **CI/CD Collision Prevention Rules**:
  - Never reuse `1.5.3-experimental` or upstream's `1.5.4-beta`.
  - Pushing to `origin/main` triggers `.github/workflows/release.yml` which automatically builds and publishes a release for the tag in `VERSION`. Therefore, keep development and verification on `perf/phase6-highspeed-streaming` (or a dedicated `perf/phase9-harmonization-1.5.4` branch), and when merging to `main`, let either `.github/workflows/release.yml` OR manual CLI release publish `v1.5.4-experimental`—never both simultaneously.
