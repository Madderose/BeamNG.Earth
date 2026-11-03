# Changelog — `dev-experimental-branch` (`1.7.3-dev-experimental`)

All notable changes on `origin/dev-experimental-branch` relative to `TecnaGamer/BeamNG.Earth` `upstream/dev` (`ad9ae5a1`, `1.7.3-beta`, `earthfast` `v142`).

Changes are organized into **4 modular PR packages** so upstream maintainers can review, test, and merge each category independently.

---

## [PR Package 1] Performance, Frame-Pacing & Shadow Culling (`pr/perf-frame-pacing-and-shadows`)
*Pure engine & streaming performance improvements — zero changes to terrain/biome data sources.*

### Added
- **Deferred Time-Sliced Building Collision Rebuild (`roads.lua`, `core.lua`)**:
  - Replaces synchronous per-tile `be:reloadCollision()` calls with a debounced collision queue (`COLLISION_QUIET_S = 1.5s`, `COLLISION_MAX_WAIT_S = 8.0s`, `COLLISION_URGENT_M = 160m`).
  - Eliminates multi-frame physics rebuild stalls when streaming dense village/urban road geotiles at high speed while guaranteeing solid building collisions whenever the vehicle is within `160 m` of an unbuilt collider.
- **Distance-Adaptive Sun Shadow & Object Shadow Culling (`shadowctl.lua`, `buildings.materials.json`, `tunnel.materials.json`, `satmat.lua`, `terrain.lua`)**:
  - Added [`shadowctl.lua`](mod/beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua) (`274` lines of unit tests in `mod/tests/test_shadowctl.lua`) to manage shadow distance and pixel-size culling (`SOLID_SHADOW_NULL_PX = 35`, `NONSOLID_SHADOW_NULL_PX = 150`).
- **First-Time C++ Shape Load Budget & Static Signal Materials (`trees.lua`, `CREDITS.md`)**:
  - Caps first-time C++ `TSStatic` / `ForestItemData` shape loads to `FIRSTS_PER_FRAME = 1` per frame while preserving `everMade` across anchor rebases (adapted from `mpsteppe`).
  - Swaps animated traffic-light boom materials to a static material (`bne_trafficlight_static`) to avoid unnecessary per-frame UV animation overhead.
- **Worker Process Priority & Windows UTF-8 Safety (`server/pools.py`, `launcher.py`, `install.py`)**:
  - Ensures background worker pools run at below-normal CPU priority so the game's render/physics threads are never starved, and enforces `PYTHONUTF8=1` across Windows subprocesses.

### Benchmark Impact (Mont Ventoux D974, `3.0 km` @ `120 mph`, DX12)
- **Hitches `>50 ms` (severe frame stalls)**: Reduced from **`2`** on `upstream/dev` to **`0`** (`-100%`).
- **Hitches `>33 ms`**: Reduced from **`6`** on `upstream/dev` to **`2`** (`-66.7%`).
- **`p99` Frame Time**: Improved from `21.15 ms` to `20.38 ms` (`-3.6%`), and worst-frame `max_ms` improved from `57.20 ms` to `45.57 ms` (`-20.3%`).

---

## [PR Package 2] Declarative Addon Architecture, Layer B Effort Governor & Live World Reload (`pr/addon-architecture-and-effort-governor`)
*Core infrastructure separating "Ground Truth" (Layer A) from "Performance Effort" (Layer B), with instant in-game toggle & live world reload.*

### Added
- **Layer A Declarative Addon Registry & Security/Approval Gate (`server/addons.py`, `mod/beamng_earth/lua/ge/extensions/beamngEarth/addons.lua`)**:
  - Discovers native BeamNG addon zips (`addons/beamng_earth_<id>.zip` or unpacked `beamng_earth_addons/<id>/addon.json`).
  - Validates `requires_beamng_earth` semver ranges (`>=1.7.0 <1.8.0`) and SHA-256 manifest hashes against `APPROVED_MANIFEST_HASHES` so only approved, version-matched addons execute.
  - Supports granular runtime toggles per addon (`set_addon_enabled`) and per data source (`set_source_enabled`) via HTTP (`/api/addons`, `/api/addons/sync`) and TCP protocol (`addons_sync` / `addons_status`).
- **Layer B Effort & Tradeoff Controller (`server/effort.py`)**:
  - Decouples **what exists in the world** (Layer A Ground Truth) from **how much CPU/GPU effort is spent synthesizing it** (Layer B Effort Governor).
  - Provides 5 built-in profiles (`low`, `balanced`, `high`, `ultra`, `auto_fps`) controlling `veg_density_scale`, `crop_row_step_scale`, `max_items_per_cell`, `ortho_tint_enabled`, and `ortho_tint_sample_budget`, plus an EMA frame-time auto-governor (`auto_fps`).
- **Live World & Vegetation Reload on Toggle (`server/earthd.py`, `server/blockworker.py`, `server/revisit.py`, `server/vegetation.py`, `core.lua`)**:
  - **Cache-Tag Isolation**: Both `revisit.py` and `vegetation.py` (`Vegetation._path`, `cell`, `ready`) key their disk and memory caches by `<addon_cache_fingerprint>_<effort_cache_tag>`. Toggling an addon or effort profile immediately switches to the matching cache namespace without corrupting or overwriting baseline cached cells.
  - **Cross-Process Worker Sync (`runtime_addon_effort.json`)**: `earthd.py` exports runtime addon/effort state to `cache_dir/runtime_addon_effort.json`; `blockworker.py` subprocesses (`road_pool`, `far_bld_pool`, `block_pools`) automatically detect `st_mtime_ns` changes and synchronize their in-process `AddonRegistry`, `EffortController`, and memory caches before building tiles.
  - **Live Tracker Reset (`Connection.reset_world_trackers()`) & `Refresh World` Action**: Toggling any addon, data source, or effort profile (or clicking `Refresh World Around You`) clears in-game vegetation/buildings (`trees.clear()`, `roads.newSession()`, `roads.incrementBldGen()`) and resets server-side streaming trackers (`self.veg`, `self.roads`, `self.signs`, `self.bldfar`/`bldsky`/`brfar`) so the surrounding world re-streams live within 1–4 seconds without restarting the game or teleporting.
- **Dedicated `Addons` UI Tab & Floating CEF Window (`earthAddonsWindow.js`, `earthSettingsStore.js`, `EarthSettingsBody.vue`, `index.js`, `settings.lua`, `ui.lua`)**:
  - Moved all Generation Addon and Effort controls out of the `World` settings tab into a dedicated **`Addons`** tab in `Pause Menu > BeamNG.Earth > Addons`.
  - Added a standalone, draggable CEF floating window (**`/ Generation Addons`**) with live switches, Effort profile pills (`Low`, `Balanced`, `High`, `Ultra`, `Auto-FPS`), **`Refresh World Around You`** button, **`Min`** (collapse to pill), and **`X`** (close completely).

---

## [PR Package 3] France & Provence Ground Truth Pack (`pr/addon-provence-ground-truth`)
*Reference regional Ground Truth addon (`beamng_earth_provence.zip`) powered by French IGN Géoplateforme WFS/WMS and Mediterranean biome rules.*

### Added
- **Reference Addon Package (`addons/beamng_earth_provence/`, `tools/package_addon.py`)**:
  - Declarative `addon.json`, `data_sources.json`, and `biomes.json` defining bbox `[42.3°N..45.2°N, 3.0°E..7.8°E]` (Provence-Alpes-Côte d'Azur, Occitanie, Vallée du Rhône).
- **French IGN Géoplateforme BD TOPO & RPG Provider (`server/ign_fr.py`, `server/mapdata.py`, `server/imagery.py`)**:
  - Fetches official IGN BD TOPO 3D building heights/materials, IGN RPG agricultural crop parcels (`vigne`, `lavande`, `olivier`, `verger`, `tournesol`), and linear hedgerows (`haie`).
- **Row-Aligned Mediterranean Crops & Aerial Orthophoto Roof Tinting (`server/vegetation.py`, `server/buildings.py`, `bne_lavender_row.dae`)**:
  - Synthesizes parcel-oriented vineyard rows, Sault lavender rows (`bne_lavender_row.dae`), olive orchards, and Mistral cypress windbreaks (`haie`).
  - Samples 20 cm IGN aerial orthophotos (`ign_orthophoto_20cm`) to tint Provence building roofs and façades with authentic local terracotta and limestone hues.

### Benchmark Impact (`provence` Disabled vs. Enabled on Mont Ventoux D974, Warm Cache)
- **Average FPS**: `58.9 FPS` (`provence` OFF) vs `58.8 FPS` (`provence` ON, `-0.17%`).
- **`1% Low` FPS**: `47.5 FPS` (`provence` OFF) vs `48.8 FPS` (`provence` ON).
- **Hitches `>50 ms`**: `0` in both runs.

---

## [PR Package 4] Automated A/B Road-Following Benchmark & Telemetry Suite (`pr/benchmark-and-telemetry-suite`)
*Reproducible in-engine road-following benchmark harness and hardware/performance telemetry tools.*

### Added
- **Autonomous OSM Road-Following Benchmark (`tools/road_bench.py`, `tools/drive_driver.lua`, `tools/mcp.py`)**:
  - Steers a vehicle along real OpenStreetMap road geometry between any two coordinates/places while capturing 20 Hz physics & frame-time telemetry.
- **Cold/Warm Multi-Branch A/B Comparator & Telemetry Capture (`tools/cold_ab_bench.py`, `tools/perf_capture.py`, `tools/sidekick.py`, `docs/COMPANION_OFFLOAD.md`)**:
  - Automates back-to-back branch and addon comparisons and generates Markdown + JSON reports with FPS, frame-time percentiles (`p50`, `p95`, `p99`, `max_ms`), hitch counts, and CPU/GPU/RAM metrics.
