# BeamNG.Earth Streaming Architecture & Performance Audit Tracker

**Date:** 2026-10-20  
**Target:** Eliminate all driving hitches and micro-stutters during high-speed streaming  
**Scope:** Full-stack audit across Server (`earthd`), IPC/Protocol, Filesystem/VFS, GE Lua Governor, and Engine Scene/Collision Pipeline.

---

## 1. Track Overview & Assignments

| Track | Domain | Focus Area | Assigned Agent | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Track 1** | **IPC, Protocol & Serialization** | Zero-copy / binary streaming, JSON parsing elimination on GE Lua main thread, message batching & pose emission throttling | `task-2492` (Argon 4 High) | `RUNNING` |
| **Track 2** | **Filesystem I/O & VFS Caching** | Eliminating C++ `ResourceManager` / `FileWatchers` stalls, RAM caching, atomic staging, asset slot recycling without disk re-reads | `task-2494` (Argon 4 High) | `RUNNING` |
| **Track 3** | **Governor, GC & Frame Budgeting** | Time-sliced proactive GC, governor token bucket dynamics, decoupling tile deserialization from frame rendering, pose burst smoothing | Active Session | `ANALYZED / RESOLVED` |
| **Track 4** | **Scene Graph, Collision & Rendering** | `be:reloadCollision()` debouncing, `DecalRoad` node regeneration batching, TSStatic pooling vs Forest, shadow cascade culling | `task-2496` (Argon 4 High) | `RUNNING` |
| **Diag** | **Performance Capture 01-12-03** | Deep frame-by-frame correlation with beamng.log and engine hitches | `task-2327` (Argon 4 High) | `RUNNING` |

---

## 2. Key Hypotheses & Areas for Scope Changes

1. **JSON Deserialization Overhead on Main Thread (Track 1):**
   - Current: Every 0.20s, tile messages with hundreds of coordinates, properties, and arrays are decoded via pure Lua `jsonDecode`.
   - Scope Change: Binary message packing (e.g. struct packing, typed arrays, msgpack) or micro-batched parsing to eliminate GC object churn.

2. **Disk I/O and OS File Watcher Contention (Track 2):**
   - Current: Every farfield shape (`.cdae`) and texture (`.dds`) is written to disk in `<userpath>/temp/beamngEarth/<sid>/`.
   - Problem: BeamNG's Torque3D engine monitors `<userpath>` via Win32 `ReadDirectoryChangesW`. Even with Lua hooks, Torque3D's C++ `ResourceManager` triggers synchronous file checks on the render thread.
   - Scope Change: In-memory slot recycling, custom VFS mount or isolating temp storage outside watched directories.

3. **Governor and GC Co-Scheduling (Track 3):**
   - Current: Incremental GC stepping ran independently of governor budgets and would either fall behind (causing 91ms stop-the-world spikes) or step too aggressively (causing 20ms frame drops).
   - Scope Change: Adaptive GC stepping dynamically tied to governor idle frame margins, never exceeding 0.3ms wall clock.

4. **Synchronous Collision & Road Rebuilding (Track 4):**
   - Current: Road tile arrivals and building placements trigger `DecalRoad` regeneration and potential physics collision rebuilds.
   - Scope Change: Asynchronous collision slicing, batched road mesh commits, and strict LOD distance clipping for shadow casters.

---

## 3. Findings Log (Syndication)

*(Findings from active agents will be appended here as they complete their investigations)*

### Diag Agent & Capture Progress:
- **`task-2327` (Diag Capture 01-12-03, Argon 4 High):** Dissected the 5 Hz rhythmic 20 ms GC hitches caused by `collectgarbage('step', 1000)` taking up to 22.5 ms per frame during 0.20s pose bursts. (Report: [`perfgraph_011203_analysis.md`](file:///c:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/perfgraph_011203_analysis.md)).
- **`task-2506` (Diag Capture 01-26-50, Argon 4 Medium):** Evaluated the 30.7s drive after reducing GC step to 30KB. Confirmed average FPS leaped from **113.9 to 147.2 FPS (+29.3%)**, $p_{50}$ dropped to **6.67 ms**, and 95% of frames ran above **66 FPS**. Lua hitches collapsed by **>90%** (from 4.1/s down to 0.39/s). Remaining bottlenecks: Frame 667 `RenderShadows = 58.8 ms` (tile batch insertion into scene quadtree) and Frame 3801 `FileWatchers = 21.6 ms` (C++ `ResourceManager` scanning DDS writes). (Report: [`perfgraph_012650_analysis.md`](file:///c:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/perfgraph_012650_analysis.md)).

---

## 4. Synthesis & Action Plan
*(To be populated following cross-agent analysis)*
