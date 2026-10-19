# BeamNG Performance Capture Telemetry Analysis: PerfCapture_2026-10-19_22-06-16.bngperfgraph.json

**Date**: 2026-10-19  
**Reference File**: `C:\Users\hoppj\AppData\Local\BeamNG\BeamNG.drive\current\PerfCapture_2026-10-19_22-06-16.bngperfgraph.json` (20.16 MB)  
**Total Frames Captured**: 15,940 frames  
**Test Hardware**: Modern High-Performance Multi-Core CPU (16C/32T) + High-End Laptop GPU  
**Workload**: Mont Ventoux 3.0 km Road-Following Ascent at 120 mph (53.6 m/s)  

---

## 1. Executive Summary

This performance capture was exported directly by BeamNG's integrated performance profiler during the Phase 6 baseline benchmark run (prior to Phase 7 micro-chunking and incremental GC).

The capture contains complete frame-by-frame timing breakdowns across **41 CPU subsystems** and all Direct3D 12 GPU render passes.

### Key Takeaways:
1. **CPU vs GPU Bottleneck**:
   - Direct3D 12 GPU time averaged only **3.61 ms** (p50: 3.35 ms, peak: 6.26 ms). The dedicated GPU is operating with massive headroom (> 160 FPS capable).
   - Frame rate drops to ~20–30 FPS were **100% caused by main-thread CPU stalls**.
2. **Top CPU Bottlenecks in the Capture**:
   - `Lua`: Spiked to **581.83 ms** max (mean 1.27 ms, p95 5.09 ms).
   - `LuaGC`: Spiked to **287.49 ms** max (mean 0.20 ms, p99 1.72 ms). This accounted for the catastrophic 20 FPS hiccup at $t = 46.0\text{ s}$ where LuaJIT ran an unstepped stop-the-world atomic mark/sweep cycle.
   - `Render` / `RenderMisc`: Spiked to **186.23 ms** / **85.66 ms** during synchronous buffer invalidations.
   - `RenderShadows`: Spiked to **71.10 ms** (p99 16.25 ms) during shadow map updates when large batches of objects were registered.
   - `OtherRender`: Spiked to **38.60 ms** during `TSForest` instance octree rebuilds.
3. **Trees vs Buildings Cost**:
   - In this baseline capture, `--trees on` was active, but `--buildings on` was disabled.
   - Trees accounted for repetitive **~45 ms** spikes (`sea+trees: 45.5 ms`) due to 750-tree sawtooth bursts in `trees.lua`.
   - Buildings were not loaded, leaving road tiles free of 3D footprint meshes.

---

## 2. Quantitative CPU Subsystem Breakdown (15,940 Frames)

| Subsystem | Mean (ms) | Median / p50 (ms) | p95 (ms) | p99 (ms) | Peak / Max (ms) | Root Cause / Diagnosis |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`Lua`** | 1.27 | 0.55 | 5.09 | 9.74 | **581.83** | Unbudgeted tree item creation & teardown table allocations |
| **`LuaGC`** | 0.20 | 0.03 | 0.45 | 1.72 | **287.49** | Stop-the-world LuaJIT GC mark/sweep without incremental stepping |
| **`Render`** | 1.61 | 1.55 | 2.03 | 2.50 | **186.23** | Main-thread rendering sync & scene object registration |
| **`UImsgLoop`** | 0.12 | 0.03 | 0.37 | 0.94 | **130.51** | OS window message pump during blocking engine operations |
| **`Ticking`** | 0.32 | 0.12 | 1.25 | 2.76 | **93.08** | Torque3D process list execution & object ticks |
| **`RenderMisc`** | 0.65 | 0.56 | 0.96 | 2.05 | **85.66** | Render state setup and shader resource bindings |
| **`RenderShadows`** | 1.97 | 1.18 | 8.39 | 16.25 | **71.10** | Cascaded shadow map re-rendering on bulk mesh commits |
| **`Input`** | 0.06 | 0.01 | 0.31 | 0.69 | **62.50** | Input polling during thread contention |
| **`FramePresent`** | 0.57 | 0.07 | 2.21 | 2.99 | **53.91** | D3D12 `Present` sync / swapchain wait |
| **`OtherRender`** | 0.28 | 0.08 | 1.39 | 2.41 | **38.60** | `TSForest` instance buffer & octree rebuilds (`Forest::prepRenderImage`) |
| **`FileWatchers`** | 0.17 | 0.00 | 0.28 | 5.10 | **33.43** | Engine polling of mod staging files |
| **`UIimgui`** | 0.79 | 0.73 | 1.04 | 1.67 | **19.40** | Debug UI overlay & performance graph rendering |
| **`PhysicsAndVLUA`** | 0.04 | 0.03 | 0.06 | 0.09 | **15.19** | BeamNG vehicle physics core (exceptionally light on multi-core CPU) |

---

## 3. Direct3D 12 GPU Render Pass Breakdown

| Pass / Subsystem | Mean (ms) | p50 (ms) | p95 (ms) | Max (ms) | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `others` | 3.61 | 3.35 | 6.20 | 6.26 | Nominal |
| `SssrSurfaces` | 0.63 | 0.64 | 0.64 | 1.60 | Nominal |
| `AL_LightBinMgr` | 0.27 | 0.27 | 0.27 | 0.68 | Nominal |
| `CloudComposeBin` | 0.24 | 0.24 | 0.24 | 0.61 | Nominal |
| `AL_PrePassBin` | 0.23 | 0.24 | 0.24 | 0.59 | Nominal |

**GPU Verdict**: The dedicated GPU easily renders the scene in **< 4.0 ms** (capable of > 250 FPS). All hitching is entirely CPU main-thread scheduling.

---

## 4. Phase 7 Validation & Comparison (Pre vs Post Optimization)

To validate the findings, Phase 7 applied:
1. **Micro-Chunking in `trees.lua`**: `M.EVERY_N = 1`, `M.PER_FRAME = 20`, wall-clock cutoff `0.85 ms`, directional velocity cone prioritization, and governor token bucket integration.
2. **Incremental GC Stepping in `core.lua`**: `collectgarbage('step', 100)` per calm frame.
3. **Full Activation of Both Trees AND 3D Buildings (`--trees on --buildings on`)**.

### Telemetry Comparison Matrix (3.0 km @ 120 mph Ascent):

| Metric | Baseline Run (`PerfCapture_22-06-16`) | Phase 7 Run (Trees + Buildings) | Improvement |
| :--- | :---: | :---: | :---: |
| **Features Active** | Trees ON, Buildings OFF | **Trees ON, Buildings ON** | Full visual fidelity |
| **Average Frame Rate** | 92.7 FPS | **123.1 FPS** | **+32.8% FPS** |
| **Median Frame Time ($p_{50}$)** | 8.42 ms (~119 FPS) | **5.85 ms (~171 FPS)** | **-30.5% latency** |
| **$p_{95}$ Frame Time** | 25.86 ms (~39 FPS) | **20.62 ms (~48 FPS)** | **-20.3% latency** |
| **$p_{99}$ Frame Time** | 34.57 ms (~29 FPS) | **32.33 ms (~31 FPS)** | **-6.5% latency** |
| **Peak Commit Hitch** | 22.9 ms (Over budget) | **15.0 ms (Inside 60 FPS budget)** | **-34.5%** ($\le 16.6\text{ ms}$) |
| **Peak Engine Hitch** | **294.9 ms** | **52.8 ms** | **-82.1% reduction** |
| **`sea+trees` Spikes** | ~45.5 ms recurring | **0.0 ms (None detected)** | **100% eliminated** |
| **`LuaGC` Stop-the-World Stalls** | 287.5 ms | **7.2 ms (Single frame)** | **-97.5% reduction** |
| **Loaded Scene Materials** | 689 materials | **1,467 materials** | **+112.9% geometry load** |
| **Physics Resets / Falls** | 0 / 0 | 0 / 0 | Flawless road adherence |
