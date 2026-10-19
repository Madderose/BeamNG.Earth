# BeamNG.Earth Streaming Architecture & Performance Audit Tracker

**Date:** 2026-10-20  
**Target:** Eliminate all driving hitches and micro-stutters during high-speed streaming  
**Scope:** Full-stack audit across Server (`earthd`), IPC/Protocol, Filesystem/VFS, GE Lua Governor, and Engine Scene/Collision Pipeline.

---

## 1. Track Overview & Assignments

| Track | Domain | Focus Area | Assigned Agent | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Track 1** | **IPC, Protocol & Serialization** | Zero-copy / binary streaming, JSON parsing elimination on GE Lua main thread, message batching & pose emission throttling | `task-2492` (Argon 4 High) | **COMPLETED** |
| **Track 2** | **Filesystem I/O & VFS Caching** | Eliminating C++ `ResourceManager` / `FileWatchers` stalls, RAM caching, atomic staging, asset slot recycling without disk re-reads | `task-2494` (Argon 4 High) | **COMPLETED** |
| **Track 3** | **Governor, GC & Frame Budgeting** | Time-sliced proactive GC, governor token bucket dynamics, decoupling tile deserialization from frame rendering, pose burst smoothing | Active Session | **VALIDATED** |
| **Track 4** | **Scene Graph, Collision & Rendering** | `be:reloadCollision()` debouncing, `DecalRoad` node regeneration batching, TSStatic pooling vs Forest, shadow cascade culling | `task-2496` (Argon 4 High) | **COMPLETED** |
| **Diag** | **Performance Captures** | Frame-by-frame correlation across baseline (22-06-16), intermediate (01-12-03), and calibrated (01-26-50) captures | `task-2327`, `task-2506` | **COMPLETED** |

---

## 2. Key Audit Findings by Track

### Track 1: IPC, Protocol & Serialization ([`track1_ipc_protocol_audit.md`](file:///c:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/track1_ipc_protocol_audit.md))
1. **Unbounded Pre-Governor JSON Deserialization:** `net.update()` reads all incoming TCP frames in an unbounded loop, and `core.lua` executes `onMessage` on all of them *before* `governor.beginFrame` starts. In dense sessions, an 8-tile burst allocates up to 72,100 Lua tables in a single frame, retaining over 370k tables in LuaJIT GC heap.
2. **Synchronized 5 Hz Server Message Storm:** `sendPoseIfDue` triggers every 0.200s (27.6 frames at 138 FPS), causing `earthd` to simultaneously push road, vegetation, building, farfield, and sea updates within the same frame interval.
3. **Quadratic String Copy in `Reassembler:pop()`:** `self.buf:sub(5 + n)` copies the entire buffer suffix on every popped message, generating ~19.6 MB of transient garbage during a 300-message burst.
4. **Missing `TCP_NODELAY` on Server Socket:** Server socket in `earthd.py` does not enable `TCP_NODELAY`, introducing Nagle buffering delays on outgoing streaming packets.

### Track 2: Filesystem I/O & VFS Pipeline ([`track2_filesystem_vfs_audit.md`](file:///c:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/track2_filesystem_vfs_audit.md))
1. **Why C++ `FileWatchers` Spikes (3.1–33.4 ms) Persist:** `hookFileWatchers()` in Lua only intercepts `_G.onFileChanged` (the final Lua dispatch). Prior to this, Torque3D's C++ directory watcher (Win32 `ReadDirectoryChangesW`) on `<userpath>` queries NTFS metadata on the main thread and triggers `ResourceManager::reloadResource` whenever pooled mesh slots (`slot_<n>.cdae`) are overwritten.
2. **Severe Write Amplification in Watched Temp:** Master `.cdae` files are written directly into watched `self.out_dir`, then hardlinked/moved again as `slot_<n>.cdae`. Staging master meshes outside the watched folder eliminates 50% of `.cdae` writes and 100% of `.cdae` deletions in `<userpath>`.
3. **Unused Disk Writes:** When `.ter` swapping is enabled, `make_heightmap` still unconditionally writes `hm_*.png` and 10 grayscale mask PNGs that the engine never loads.
4. **Synchronous `fileExists` Syscalls:** `satmat.lua` and `farfield.lua` invoke multiple synchronous `FS:fileExists()` calls on the main thread per tile.

### Track 3: Governor, GC & Frame Budgeting ([`perfgraph_012650_analysis.md`](file:///c:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/perfgraph_012650_analysis.md))
1. **The 1000 KB GC Trap:** Stepping 1000 KB (`collectgarbage('step', 1000)`) attempted to sweep 1 MB of small Lua tables in a single frame, costing 15–22.5 ms every 0.20s.
2. **Calibrated 30 KB Stepping:** Reducing step size to 30 KB maintained smooth GC collection at ~3.9 MB/s, slashing Lua hitches by **>90%** (from 4.1/s to 0.39/s) and boosting average FPS to **147.2 FPS**.

### Track 4: Scene Graph, Collision & Rendering ([`track4_scenegraph_render_audit.md`](file:///c:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/track4_scenegraph_render_audit.md))
1. **"Ghost Bridge" Vulnerability (P1-A):** In `roads.lua`, `RELOAD_DRIVE_MAX_S = 60` defers collision rebuilds while driving faster than 3 m/s. At 40–50 m/s, the car leaves its 600m collision bubble in 14s, leaving upcoming bridges, tunnels, and curbs completely intangible for the remaining 46 seconds!
2. **Collision Isolation Spike (P1-B):** `roads.lua` calls `be:reloadCollision()` without registering quiet frames in `governor.lua`, causing 12–56 ms BVH swaps to collide with farfield tile imports.
3. **Dead Road Chunks JSON Deserialization (P2-A):** Server still serializes 50–250 KB of `chunks` arrays in `roads_*.json` even when `road_mesh` (`.cdae`) is used, wasting main-thread parse time.
4. **Shadow Cascade Quadtree Fragmentation (P3-A):** Farfield meshes, `bldfar` meshes, and outer-ring billboard vegetation leave shadow casting enabled, causing recurring 58.8 ms `RenderShadows` spikes during tile batch swaps.

---

## 3. Prioritized Implementation Roadmap

| Priority | Track | Item | Target File(s) | Expected Benefit |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | Track 4 | **Fix "Ghost Bridge" collision deferral:** Replace 60s hard drive timer with distance-horizon trigger (250m ahead or >60% radius traveled). | `mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua` | Eliminates falling through bridge decks and curbs at high speeds. |
| **P1** | Track 4 | **Collision Governor Isolation Gate:** Enforce `gov.blocked = true` on collision reload frame and subsequent frame to protect physics BVH swaps. | `mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua`, `core.lua` | Eliminates multi-subsystem compound collision hitches. |
| **P2** | Track 1 | **Fix $O(M \cdot B)$ string buffer copy:** Replace `buf:sub(5 + n)` with integer read cursor in `Reassembler:pop()`. | `mod/beamng_earth/lua/ge/extensions/beamngEarth/framing.lua` | Eliminates ~20 MB of transient string garbage during message bursts. |
| **P2** | Track 1 & 4 | **Omit Dead Road Chunks from JSON:** Only serialize `chunks` when `road_mesh` is not generated. | `server/roads.py`, `mod/.../roads.lua` | Saves 50–250 KB JSON parse per tile on main thread. |
| **P2** | Track 4 | **Disable Shadow Casting on Farfield & Outer Meshes:** Set `castShadows = false` on farfield terrain tiles and distant building footprints. | `mod/.../farfield.lua`, `mod/.../trees.lua` | Eliminates 58.8 ms `RenderShadows` cascade re-indexing spikes. |
| **P3** | Track 2 | **Isolate Staging from Watched Mod Path:** Write temporary master `.cdae` files to external directory outside `<userpath>/temp/`. | `server/staging.py`, `server/earthd.py` | Eliminates 50% of Torque3D `ReadDirectoryChangesW` / `FileWatchers` C++ stalls. |
| **P3** | Track 2 | **Suppress Unused PNG Masks in `.ter` Mode:** Skip grayscale mask PNG writes when follow-block `.ter` swap is active. | `server/earthd.py`, `server/surface.py` | Eliminates 11 disk writes per terrain block transition. |
| **P4** | Track 1 | **Time-Sliced Inbound IPC & Binary Vegetation:** Cap frame message processing at 0.5 ms and stream vegetation via compact binary records. | `mod/.../net.lua`, `mod/.../trees.lua`, `server/vegetation.py` | Eliminates 370k Lua table allocations and bounds network frame cost. |
