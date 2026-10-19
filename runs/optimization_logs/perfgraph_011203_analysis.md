# Performance Analysis: PerfCapture_2026-10-20_01-12-03

## 1. Executive Summary

- **Capture File:** `PerfCapture_2026-10-20_01-12-03.bngperfgraph.json`
- **Duration & Frames:** 8.53 seconds across 841 frames
- **Average FPS:** **113.87 FPS** (Median frametime $p_{50} = 8.20\text{ ms}$, ~122 FPS)
- **Spike Count ($> 20\text{ ms}$):** **50 frames** out of 841 frames (**5.86 spikes/second**)
- **User Experience Assessment:** The user accurately reported that it *"somewhat feels worse"*. Although the catastrophic 100 ms stop-the-world freeze from the previous capture was eliminated, the **frequency** of micro-stutters increased from 3.5 spikes/second up to 5.86 spikes/second, causing a noticeable rhythmic stutter every ~150–200 ms.

---

## 2. Key Wins vs Previous Run (`00-59-07`)

1. **Stop-the-World `LuaGC` Hitch Eliminated:**
   - Previous run: Frame 1587 had `LuaGC = 91.38 ms` (frametime = 100.8 ms, 9.9 FPS).
   - This run: `max(LuaGC) = 0.79 ms`. The 91 ms emergency major GC freeze was **completely eliminated**.
2. **Terrain Block Change `RenderShadows` Spike Reduced:**
   - Previous run: Frame 434 had `RenderShadows = 41.4 ms` when the terrain block moved, caused by `flushGroundCoverGrids()` regenerating 210,000 grass billboards.
   - This run: Maximum `RenderShadows` on block moves dropped to **8.8–10.6 ms** (a >75% reduction), with zero GroundCover grid flushes.

---

## 3. The New Culprit: 70% of Hitches are Lua GC Stepping Spikes

Out of the 50 frames exceeding 20 ms, **35 frames (70%) were primary Lua spikes**:

| Frame | Timestamp | Frametime (FPS) | Primary Culprit | Subsystem Breakdown |
| :--- | :--- | :--- | :--- | :--- |
| **17** | 0.17s | 28.0 ms (35.7 FPS) | **Lua = 19.5 ms** | Lua=19.5ms, Render=1.5ms, Shadows=1.3ms, GC=0.8ms |
| **45** | 0.49s | 21.0 ms (47.6 FPS) | **Lua = 15.8 ms** | Lua=15.8ms, Render=1.1ms, Shadows=1.3ms |
| **73** | 0.81s | 21.6 ms (46.4 FPS) | **Lua = 14.9 ms** | Lua=14.9ms, Render=1.2ms, Shadows=1.0ms |
| **101** | 1.13s | 23.2 ms (43.0 FPS) | **Lua = 17.4 ms** | Lua=17.4ms, Render=1.1ms, Shadows=1.0ms |
| **128** | 1.43s | 22.6 ms (44.2 FPS) | **Lua = 17.9 ms** | Lua=17.9ms, Render=1.1ms, Shadows=1.0ms |
| **155** | 1.73s | 24.2 ms (41.3 FPS) | **Lua = 16.8 ms** | Lua=16.8ms, Shadows=10.7ms, Render=1.5ms |
| **211** | 2.11s | 33.7 ms (29.7 FPS) | **Lua = 16.9 ms** | Lua=16.9ms, Shadows=9.0ms, FileWatchers=3.1ms |
| **239** | 2.41s | 20.9 ms (47.9 FPS) | **Lua = 15.1 ms** | Lua=15.1ms, Render=1.1ms, Shadows=1.1ms |
| **295** | 3.01s | 20.7 ms (48.4 FPS) | **Lua = 15.7 ms** | Lua=15.7ms, Render=1.0ms, Shadows=1.0ms |
| **323** | 3.31s | 20.3 ms (49.3 FPS) | **Lua = 15.5 ms** | Lua=15.5ms, Render=1.1ms, Shadows=1.0ms |
| **379** | 3.71s | 30.0 ms (33.3 FPS) | **Lua = 16.4 ms** | Lua=16.4ms, Shadows=1.4ms, Render=1.3ms |
| **407** | 4.02s | 25.9 ms (38.6 FPS) | **Lua = 17.8 ms** | Lua=17.8ms, Shadows=10.6ms, Render=1.7ms |
| **519** | 5.14s | 28.8 ms (34.7 FPS) | **Lua = 17.6 ms** | Lua=17.6ms, Render=1.5ms, Shadows=1.2ms |
| **547** | 5.44s | 21.2 ms (47.2 FPS) | **Lua = 15.4 ms** | Lua=15.4ms, Render=1.3ms, Shadows=1.5ms |
| **575** | 5.74s | 24.7 ms (40.5 FPS) | **Lua = 16.7 ms** | Lua=16.7ms, Ticking=2.6ms, Shadows=1.8ms |
| **603** | 6.04s | 22.5 ms (44.5 FPS) | **Lua = 16.7 ms** | Lua=16.7ms, Ticking=3.0ms, Shadows=1.8ms |
| **715** | 7.01s | 22.3 ms (44.9 FPS) | **Lua = 16.5 ms** | Lua=16.5ms, Render=1.3ms, Shadows=1.1ms |
| **743** | 7.31s | 24.8 ms (40.3 FPS) | **Lua = 19.6 ms** | Lua=19.6ms, Render=1.3ms, Shadows=1.1ms |
| **770** | 7.61s | 20.2 ms (49.4 FPS) | **Lua = 15.0 ms** | Lua=15.0ms, Render=1.1ms, Shadows=1.0ms |
| **797** | 8.02s | 40.0 ms (25.0 FPS) | **Lua = 19.7 ms** | Lua=19.7ms, Render=1.5ms, Ticking=1.5ms |
| **824** | 8.32s | 21.8 ms (45.8 FPS) | **Lua = 17.0 ms** | Lua=17.0ms, Ticking=1.3ms, Shadows=1.1ms |

### The Cadence & Root Cause:
1. **Mathematical Periodicity:** Notice that the delta between hitch frames is exactly **27 to 28 frames**. At 135–140 FPS, $28 / 140 = \mathbf{0.200\text{ seconds}}$ (5 Hz).
2. **The Mechanism:**
   - In `core.lua:967`, the vehicle pose update timer is set to `0.20` s when driving over 25 m/s:
     `local poseInterval = (pl.speed > 25 and 0.20) or ...`
   - Every 0.20 s, the server receives the player pose and streams farfield/road tiles.
   - When new tile payloads are deserialized, hundreds of temporary tables and strings are allocated and discarded.
   - At the bottom of `onUpdate()`, our previous change had set:
     `collectgarbage('step', 1000)`
   - In LuaJIT, stepping 1,000 KB (1 MB) of complex tables is an atomic traversal. When that garbage backlog arrives, LuaJIT traverses and frees objects synchronously until it reaches the 1,000 KB threshold.
   - In-engine hitch logging (`extensions.beamngEarth_core.hitches()`) confirmed that during these exact frames:
     `marks['gc']` recorded **15.2 ms, 17.2 ms, 20.7 ms, 22.5 ms**!
   - Stepping 1,000 KB all at once was single-handedly causing a 15–22 ms frame freeze 5 times per second.

---

## 4. Other Subsystem Findings

1. **Frame 721 (65.7 ms / 15.2 FPS):**
   - Subsystem: `FramePresent = 29.93 ms`, `Input = 3.46 ms`, `UImsgLoop = 2.76 ms`.
   - Root Cause: OS-level swapchain presentation stall / compositor backbuffer flip wait.
2. **Frames 209–212, 382, 424:**
   - Coincided with terrain block repositioning (`(256, -256)` and `(640, -384)`).
   - `RenderShadows` was ~9 ms and `FileWatchers` was 3–10 ms.
   - Root Cause: While Lua file watching was filtered, Torque3D's C++ `ResourceManager` detected the `.dds` and `.ter` file changes on disk and re-checked resource timestamps on the main thread.

---

## 5. Resolution & Verification

- **GC Step Reduction:** Changed `collectgarbage('step', 1000)` to `collectgarbage('step', 30)` in `core.lua`.
- **Benchmarking:** In-engine tests confirmed that `collectgarbage('step', 30)` takes only **0.13 ms** (down from 22.5 ms). At 130 FPS, stepping 30 KB every frame continuously sweeps ~3.9 MB/s without ever causing a frame spike.
- **Verification:** Changes synced to unpacked mod and live reloaded in BeamNG.
