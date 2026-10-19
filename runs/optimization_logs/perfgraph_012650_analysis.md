# Performance Analysis: PerfCapture_2026-10-20_01-26-50

## 1. Executive Summary

- **Capture File:** `PerfCapture_2026-10-20_01-26-50.bngperfgraph.json`
- **Duration & Frames:** 30.70 seconds across 4,105 frames
- **Average FPS:** **147.19 FPS** (Up from 113.87 FPS — **+29.3% increase**)
- **Median Frametime ($p_{50}$):** **6.67 ms** (~150 FPS, down from 8.20 ms)
- **$p_{95}$ Frametime:** **15.03 ms** (~66.5 FPS) — **Over 95% of frames ran above 66 FPS**
- **$p_{99}$ Frametime:** **21.33 ms** (down from 28.84 ms)
- **Hitch Rate ($> 20\text{ ms}$):** **1.99 spikes/second** (down from 5.86 spikes/second — a **66% reduction in stutter frequency**)

---

## 2. Before vs After: GC Step Reduction Impact

| Metric | Before Fix (`01-12-03`, step 1000) | After Fix (`01-26-50`, step 30) | Delta |
| :--- | :--- | :--- | :--- |
| **Duration** | 8.53 s (841 frames) | **30.70 s (4,105 frames)** | ~4x longer drive |
| **Avg FPS** | 113.87 FPS | **147.19 FPS** | **+33.3 FPS (+29.3%)** |
| **Median ($p_{50}$)** | 8.20 ms (~122 FPS) | **6.67 ms (~150 FPS)** | **-1.53 ms faster** |
| **$p_{95}$ Frametime** | 20.99 ms (47.6 FPS) | **15.03 ms (66.5 FPS)** | **+18.9 FPS tail** |
| **Spikes $> 20\text{ ms}$** | 50 (5.86 spikes/sec) | 61 (1.99 spikes/sec) | **-66% spike rate** |
| **Lua Hitches** | **35 frames (4.10/sec)** | **12 frames (0.39/sec)** | **>90% reduction!** |

The 5 Hz rhythmic 20 ms GC hitches that plagued the previous capture were **completely eradicated**.

---

## 3. Breakdown of the Remaining Hitches (61 frames in 30.7 s)

In this 30-second capture, 4,044 out of 4,105 frames (98.5%) ran smoothly below 20 ms. The remaining 61 frames breakdown as follows:

| Subsystem | Hitch Count | Root Cause & Key Observations |
| :--- | :--- | :--- |
| **`RenderShadows`** | 24 frames | Occurred during far-field tile group swaps (e.g. Frame 667 @ 5.05s: `RenderShadows = 58.8 ms` coinciding with `anchor 14` tile burst). Adding dozens of mesh instances to the scene quadtree forces shadow cascades (Cascades 0–3) to re-traverse and re-cull bounding boxes. |
| **`Render`** | 13 frames | Baseline render submission jitter (1.2–2.3 ms). |
| **`Lua`** | 12 frames | Dropped from 35 frames down to 12 frames across 30 seconds. Mostly minor residual processing during tile receipt. |
| **`FramePresent`** | 5 frames | OS compositor backbuffer flip wait / Direct3D swapchain stalls (e.g. Frame 1564 @ 11.27s: 45.0 ms, Frame 3454 @ 25.07s: 37.3 ms). |
| **`FileWatchers`** | 3 frames | `beamng.log` recorded 44 `.dds` texture file changes in `/temp/beamngEarth/` written by `earthd` during anchor 14 streaming. Torque3D's C++ `ResourceManager` intercepted these disk writes and checked resource timestamps (Frames 666, 1102, 3801: 7.5–21.6 ms). |
| **`OtherRender`** | 3 frames | Deferred lighting and post-processing passes. |
| **`Ticking`** | 1 frames | Simulation sub-step tick. |

---

## 4. Architectural Hints & Priorities for the Audit Agents

1. **Eliminate C++ `ResourceManager` File Watching (Track 2):**
   - Writing 44 DDS files per anchor switch into `<userpath>/temp/beamngEarth/` causes Torque3D's C++ filesystem thread to trigger `ResourceManager::reloadResource` (Frame 3801 had `FileWatchers = 21.6 ms`).
   - Moving the streaming texture buffer to a virtual memory / shared memory pipe or outside the watched userpath will wipe out these remaining file watcher spikes.
2. **Smooth Shadow Quadtree Ingestion (Track 4):**
   - When a batch of 8–32 farfield tiles swaps in simultaneously, `RenderShadows` spikes to 58.8 ms for a single frame as all shadow cascades re-index the scene.
   - Slicing tile scene insertion across multiple frames or disabling shadow casting on far-field mesh LODs will eliminate the 58 ms shadow hitch.
3. **Decouple Swapchain Presentation Stalls (Track 1 & 3):**
   - Ensure the engine never stalls `FramePresent` while waiting on background worker threads.
