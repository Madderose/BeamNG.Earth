# Performance Analysis: PerfCapture_2026-10-20_01-26-50

**Date:** 2026-10-20  
**Capture File:** `C:\Users\hoppj\AppData\Local\BeamNG\BeamNG.drive\current\PerfCapture_2026-10-20_01-26-50.bngperfgraph.json` (5.07 MB)  
**Correlated Log:** `C:\Users\hoppj\AppData\Local\BeamNG\BeamNG.drive\current\beamng.log` (`t_log = 201.03s .. 231.73s`, Anchor #15 at Mont Ventoux `44.17128, 5.13917`)  
**Hardware:** AMD Ryzen 9 9955HX3D (16C/32T) + NVIDIA GeForce RTX 5080 Laptop GPU (Direct3D 12)  
**Configuration Change Under Test:** Incremental Lua GC reduced from `collectgarbage('step', 1000)` to `collectgarbage('step', 30)` in `core.lua`

---

## 1. Executive Summary & Core Telemetry Metrics

### 1.1 Capture Summary (`PerfCapture_2026-10-20_01-26-50`)
- **Duration:** **30.70 seconds** (`30.702 s`)
- **Total Frame Count:** **4,105 frames**
- **FPS Metrics:**
  - **Minimum FPS:** **15.54 FPS** (Frame 668, `64.37 ms`)
  - **Average FPS (Arithmetic Mean):** **147.19 FPS**
  - **Effective FPS (Harmonic Mean, $\text{Frames}/\text{Duration}$):** **133.70 FPS**
  - **Median FPS ($p_{50}$):** **149.82 FPS**
  - **Maximum FPS:** **249.92 FPS** (`4.00 ms`)
- **Frametime Percentiles ($1000 / \text{FPS}$):**
  - **Minimum:** **4.00 ms**
  - **Mean:** **7.48 ms**
  - **$p_{50}$ (Median):** **6.67 ms** (149.8 FPS)
  - **$p_{90}$:** **9.11 ms** (109.8 FPS)
  - **$p_{95}$:** **15.03 ms** (66.5 FPS — well within the 16.67 ms / 60 FPS budget)
  - **$p_{99}$:** **21.32 ms** (46.9 FPS)
  - **Maximum:** **64.37 ms** (15.5 FPS at Frame 668)
- **Hitch Frame Counts:**
  - **Frames $> 20.0\text{ ms}$ (< 50 FPS):** **61 frames** (**1.49%** of all frames, **1.99 spikes/second**)
  - **Frames $> 16.67\text{ ms}$ (< 60 FPS):** **138 frames** (**3.36%** of all frames, **4.49 spikes/second**)
  - **Frames $> 33.33\text{ ms}$ (< 30 FPS):** **3 frames** (**0.07%** of all frames, **0.10 spikes/second** — Frames 668, 1565, 3455)

### 1.2 Progression Across Recent Captures

| Metric | `00-59-07` (Unstepped GC) | `01-12-03` (`step = 1000`) | `01-26-50` (`step = 30`) | Change (`01-12-03` $\to$ `01-26-50`) |
| :--- | :---: | :---: | :---: | :---: |
| **Duration / Frames** | 16.24 s / 1,885 | 8.53 s / 841 | **30.70 s / 4,105** | +260% sample duration |
| **Arithmetic Avg FPS** | 130.10 FPS | 113.87 FPS | **147.19 FPS** | **+29.3% FPS** |
| **Effective Avg FPS ($N/T$)** | 116.06 FPS | 98.58 FPS | **133.70 FPS** | **+35.6% FPS** |
| **Median Frametime ($p_{50}$)** | 7.28 ms | 8.20 ms | **6.67 ms** | **-18.7% frametime** |
| **$p_{95}$ Frametime** | 17.94 ms | 20.99 ms | **15.03 ms** | **-28.4% (now $< 16.67\text{ ms}$)** |
| **$p_{99}$ Frametime** | 25.23 ms | 28.81 ms | **21.32 ms** | **-26.0% frametime** |
| **Max Frametime (Min FPS)** | 100.83 ms (9.9 FPS) | 65.73 ms (15.2 FPS) | **64.37 ms (15.5 FPS)** | -36.2% vs unstepped |
| **Hitches $> 20\text{ ms}$ (Rate)** | 57 (**3.51 / s**) | 50 (**5.86 / s**) | 61 (**1.99 / s**) | **-66.1% hitch frequency** |
| **`Lua` Mean / $p_{95}$ / $p_{99}$** | 0.89 / 2.53 / 6.61 ms | 2.97 / 10.64 / 16.87 ms | **0.82 / 1.70 / 5.07 ms** | **-84.0% at $p_{95}$** |
| **`Lua` Spikes $> 14\text{ ms}$** | 0 (0.00 / s) | 31 (**3.63 / s**) | **1 (0.03 / s)** | **-99.1% elimination** |
| **`Lua` Spikes $> 10\text{ ms}$** | 1 (0.06 / s) | 56 (**6.56 / s**) | **5 (0.16 / s)** | **-97.5% reduction** |
| **`LuaGC` Mean / $p_{99}$ / Max** | 0.09 / 0.41 / **91.38 ms** | 0.06 / 0.70 / 0.87 ms | **0.06 / 0.48 / 9.19 ms** | -89.9% max vs unstepped |

---

## 2. Are the 28-Frame / 0.20s Lua Spikes Gone?

**Yes — the 5 Hz (every 27–28 frames / 0.20s) periodic `Lua` GC stepping spikes are 100% gone.**

1. **Elimination of the 5 Hz Sawtooth:**
   - In `PerfCapture_2026-10-20_01-12-03`, `collectgarbage('step', 1000)` attempted to traverse and sweep 1 MB of Lua tables every time a 5 Hz (`0.20s`) server pose response arrived, producing 35 hitch frames ($>20\text{ ms}$) in 8.53 seconds (`4.10 Lua hitches/sec`) with `Lua` spiking to `14.9–19.7 ms` every 27–28 frames.
   - In `PerfCapture_2026-10-20_01-26-50` with `collectgarbage('step', 30)`, `Lua` median time dropped to **0.57 ms** and $p_{95}$ dropped from **10.64 ms down to 1.70 ms** (-84%).
   - Across all 4,105 frames (30.70 seconds), there is **zero 28-frame periodicity**. Only **1 frame** in the entire 30.7-second capture had `Lua > 14 ms` (`Frame 1940` at `23.80 ms`), and only **5 frames** had `Lua > 10 ms` (`0.16/s` vs `6.56/s` previously).

2. **Nature of the Remaining Isolated `Lua` / `LuaGC` Spikes:**
   - **Pre-Governor TCP JSON Burst Deserialization (`Lua` = 10.3–23.8 ms on 5 frames):**
     - `Frame 650 (t=4.91s)`: `Lua = 11.15 ms` (compound with `RenderShadows = 10.10 ms`, `FileWatchers = 3.10 ms`, `RenderMisc = 3.02 ms`).
     - `Frame 1940 (t=13.99s)`: `Lua = 23.80 ms`, `LuaGC = 6.84 ms` (`FT = 28.72 ms`).
     - `Frame 3647 (t=26.70s)`: `Lua = 10.95 ms` (compound with `RenderShadows = 7.81 ms`, `FT = 23.55 ms`).
     - `Frame 3752 (t=27.69s)`: `Lua = 10.30 ms` (compound with `FramePresent = 10.12 ms`, `FT = 17.45 ms`).
     - `Frame 3789 (t=28.03s)`: `Lua = 10.58 ms` (part of a 3-frame tile arrival burst `F3787..F3789` where `Lua` was `9.97 ms, 6.07 ms, 10.58 ms`, `FT = 15.53–16.84 ms`).
     - **Root Cause:** As identified in Track 1 (`net.lua` / `core.lua`), `net.update()` drains all incoming TCP messages and runs `jsonDecode` *before* `governor.beginFrame()`. When `earthd` flushes a multi-tile batch simultaneously, decoding tens of thousands of JSON table nodes spikes `Lua` on that single arrival frame.
   - ** Terrain Block Repositioning (`Lua` = 6.80–7.58 ms on 2 frames):**
     - `Frame 1454 (t=10.46s, log=211.49s)`: `Lua = 6.80 ms`, `FT = 12.05 ms` — correlates to the exact millisecond with `beamng.log`: `terrain block now at (768, -512), 6.5 ms`.
     - `Frame 3734 (t=27.53s, log=228.56s)`: `Lua = 7.58 ms`, `FT = 14.32 ms` — correlates to the exact millisecond with `beamng.log`: `terrain block now at (512, -640), 7.3 ms`.
     - Neither terrain block move caused a $>20\text{ ms}$ hitch on its `Lua` execution frame!
   - **Bounded Automatic `LuaGC` Steps During Allocation Bursts (`LuaGC` = 6.84–9.19 ms on 4 frames):**
     - `Frame 334 (t=2.18s)`: `LuaGC = 7.84 ms` (`FT_next = 17.57 ms`, below 20 ms hitch threshold).
     - `Frame 717 (t=5.45s)`: `LuaGC = 9.19 ms` (`FT_next = 15.77 ms`, within 60 FPS budget).
     - `Frame 1916 (t=13.82s)`: `LuaGC = 9.08 ms` (`FT_next = 15.64 ms`, within 60 FPS budget).
     - `Frame 1940 (t=13.99s)`: `LuaGC = 6.84 ms` (coinciding with the `23.80 ms` `Lua` JSON burst).
     - Because `collectgarbage('step', 30)` keeps the heap continuously swept at ~3.9 MB/s during calm frames, even when a sudden multi-tile JSON allocation burst triggers LuaJIT's internal debt collector mid-allocation, the automatic GC step only takes **6.8–9.2 ms** (keeping 3 of the 4 occurrences under 17.6 ms, and eliminating the 91–287 ms stop-the-world stalls).

---

## 3. CPU & GPU Subsystem Breakdown (All 4,105 Frames)

### 3.1 CPU Subsystems Statistical Table

| Subsystem | Mean (ms) | Median / $p_{50}$ (ms) | $p_{95}$ (ms) | $p_{99}$ (ms) | Peak / Max (ms) | Peak Frame ($t_{\text{cap}}$) | Primary Role & Spike Diagnosis |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`RenderShadows`** | 1.30 | 0.74 | **8.00** | **10.75** | **58.75** | F667 (5.07s) | Shadow cascade quadtree re-rendering on mesh/tile commits |
| **`FramePresent`** | 1.22 | 0.91 | **3.20** | **4.48** | **45.00** | F1564 (11.28s) | D3D12 `IDXGISwapChain::Present` / DXGI compositor wait |
| **`RenderMisc`** | 0.48 | 0.43 | 0.64 | 0.96 | **24.46** | F3730 (27.47s) | D3D12 resource binding / `.ter` heightmap texture upload |
| **`Lua`** | 0.82 | 0.57 | 1.70 | **5.07** | **23.80** | F1940 (13.99s) | GE Lua `onUpdate`, pre-governor TCP JSON decode & scene commits |
| **`FileWatchers`** | 0.10 | 0.00 | 0.18 | **3.10** | **21.62** | F3801 (28.18s) | Torque3D C++ `ReadDirectoryChangesW` & `reloadResource` on `<userpath>/temp` |
| **`OtherRender`** | 0.37 | 0.06 | 1.62 | 2.12 | **19.20** | F503 (3.67s) | `TSForest` octree / instance buffer prep (`Forest::prepRenderImage`) |
| **`LuaGC`** | 0.06 | 0.03 | 0.22 | 0.48 | **9.19** | F717 (5.45s) | LuaJIT incremental GC (`step=30` + bounded burst steps) |
| **`Input`** | 0.04 | 0.01 | 0.07 | 0.53 | **8.74** | F32 (0.20s) | DirectInput polling |
| **`Render`** | 1.37 | 1.34 | 1.78 | 2.13 | **6.53** | F194 (1.22s) | Main-thread scene traversal & draw submission |
| **`Ticking`** | 0.36 | 0.16 | 1.53 | 1.88 | **5.43** | F1902 (13.71s) | Torque3D object tick list execution |
| **`UImsgLoop`** | 0.05 | 0.00 | 0.16 | 0.72 | **3.87** | F700 (5.33s) | Win32 window message pump |
| **`UIimgui`** | 0.60 | 0.58 | 0.70 | 0.93 | **1.80** | F1810 (13.15s) | ImGui profiler overlay rendering |
| **`RenderReflections`** | 0.30 | 0.29 | 0.37 | 0.61 | **1.75** | F1564 (11.28s) | Reflection probe / planar reflection pass |
| **`LuaPre`** | 0.12 | 0.11 | 0.19 | 0.26 | **1.07** | F1206 (8.91s) | Pre-tick Lua hook |
| **`PhysicsNodes`** | 0.10 | 0.10 | 0.11 | 0.13 | **0.30** | F3959 (29.46s) | Vehicle physics nodes |
| **`PhysicsAndVLUA`** | 0.03 | 0.02 | 0.04 | 0.06 | **0.24** | F3170 (22.81s) | Vehicle Lua & physics sync |

### 3.2 Direct3D 12 GPU & Memory Telemetry
- **GPU Render Passes:** Constant and effortlessly within budget (`ShadowMapPass = 1.25 ms`, `UpscaleDispatch = 1.04 ms`, `AL_PrePassBin = 0.92 ms`, `AL_LightBinMgr = 0.34 ms`; total GPU time $\approx 4.18\text{ ms}$, capable of $>235\text{ FPS}$). All hitches are strictly CPU/presentation bound.
- **Process Memory (`processPhysUsed` / `processVirtUsed`):** Stable throughout the 30.7s drive, starting at **4,319.1 MB** physical (`7,367.0 MB` virtual) and ending at **4,373.2 MB** physical (`7,584.2 MB` virtual), confirming that `collectgarbage('step', 30)` prevents unbounded memory growth.

---

## 4. Primary Causes of the 61 Remaining Hitch Frames ($> 20\text{ ms}$)

> [!NOTE]
> **Profiler Frame-Index Alignment:** In BeamNG's performance graph exporter, `FPS[i]` (`1000 / dt`) is recorded at the start of frame `i` and therefore measures the wall-clock duration of frame `i-1` when a stall occurs late in the frame pipeline (`RenderShadows`, `RenderMisc`, `OtherRender`, `FramePresent`), or aligns with `CPU[i]` during multi-frame streaming bursts. Our classification below correlates each `FT[i] > 20 ms` hitch with the exact CPU subsystem stall in frame `i` or `i-1` that produced that frame duration.

### 4.1 Hitch Breakdown by Bottleneck Category

| Rank | Bottleneck Category | Hitch Frames ($>20\text{ ms}$) | Share of Hitches | Hitch Rate (per sec) | Typical Frametime Range | Max Hitch (Frame) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | **Compound: `RenderShadows` + `FileWatchers` (+ `Lua`)** | **17** | **27.9%** | 0.55 / s | 20.17 – 30.75 ms | **30.75 ms** (F1102) |
| **2** | **`RenderShadows` (Shadow Cascade Rebuilds)** | **16** | **26.2%** | 0.52 / s | 20.06 – 64.37 ms | **64.37 ms** (F668 / CPU@F667) |
| **3** | **`FramePresent` (D3D12 Swapchain / Present Stalls)** | **15** | **24.6%** | 0.49 / s | 20.02 – 51.78 ms | **51.78 ms** (F1565 / CPU@F1564) |
| **4** | **Compound: `RenderShadows` + `Lua`** | **7** | **11.5%** | 0.23 / s | 20.39 – 23.65 ms | **23.65 ms** (F1099) |
| **5** | **`Lua` + `LuaGC` (Pre-Governor IPC Tile Burst)** | **3** | **4.9%** | 0.10 / s | 23.55 – 31.11 ms | **31.11 ms** (F650) |
| **6** | **`RenderMisc` (D3D12 Resource / `.ter` Upload Stall)** | **2** | **3.3%** | 0.07 / s | 23.75 – 30.87 ms | **30.87 ms** (F3731 / CPU@F3730) |
| **7** | **`OtherRender` (`TSForest` Octree / Buffer Prep)** | **1** | **1.6%** | 0.03 / s | 24.74 ms | **24.74 ms** (F504 / CPU@F503) |
| — | **Total Hitch Frames ($> 20\text{ ms}$)** | **61** | **100.0%** | **1.99 / s** | **20.02 – 64.37 ms** | **64.37 ms** |

---

### 4.2 Deep-Dive into the New Bottlenecks & `beamng.log` Correlations

Using the exact timestamp alignment **`t_log = t_cap + 201.030 s`** (validated to `< 5 ms` against `terrain block now at (768, -512)` at `t_log = 211.489s` / `F1454` and `terrain block now at (512, -640)` at `t_log = 228.559s` / `F3734`), every major hitch cluster maps directly to engine and filesystem events:

#### Bottleneck #1: `RenderShadows` Cascade Rebuilds (Involved in 40 of 61 Hitches — 65.6%)
- **Standalone (`16 hitches`) + Compound with `FileWatchers`/`Lua` (`24 hitches`):**
  - Normally, `RenderShadows` takes **0.74 ms** ($p_{50}$). However, whenever new 3D meshes (`slot_*.cdae`, `tunnel_*.cdae`, `bldfar_*.cdae`, `far_*.dds`) or vegetation batches are committed to the Torque3D scene graph, `RenderShadows` jumps to a quantized plateau of **8.0–17.7 ms** for several consecutive frames, and peaked once at **58.75 ms** (`Frame 667`, producing the worst hitch in the capture: `64.37 ms` / `15.54 FPS` at `Frame 668`, immediately followed by a `+271.97 MB` virtual memory commit).
- **Root Cause:** Farfield terrain meshes (`farfield.lua`), distant building batches (`bldfar`), tunnel meshes (`tunnel_15_*.cdae`), and outer-ring trees leave shadow casting enabled (`castShadows = true`), forcing Torque3D's Cascaded Shadow Map (CSM) manager to invalidate and rebuild shadow frustum quadtrees and re-render all shadow cascades on the main thread during tile streaming.

#### Bottleneck #2: C++ `FileWatchers` + `ResourceManager::reloadResource` (Involved in 17 of 61 Hitches — 27.9%)
- **Observed Spikes:** `FileWatchers` peaked at **21.62 ms** (`Frame 3801`, `FT = 29.61 ms`), **14.13 ms** (`Frame 3655`, `FT = 27.77 ms`), **13.08 ms** (`Frame 3552`, `FT = 21.06 ms`), **9.12 ms** (`Frame 1105`, `FT = 24.86 ms`), and **8.49 ms** (`Frame 1102`, `FT = 30.75 ms`).
- **Direct Correlation with `beamng.log` & Disk Writes:**
  - `t_log = 203.363s (t_cap = 2.333s, Frame 343)`: `beamng.log` records `ResourceManager::reloadResource| File changed [/temp/beamngEarth/20261020-004535-ad61/far_15_1_5_-2.dds]` + `tunnel_15_5_-4.cdae` creation $\to$ **Frame 343** spikes to **`FT = 23.01 ms`** (`RenderShadows = 8.95 ms`, `FileWatchers = 6.79 ms`).
  - `t_log = 203.959s (t_cap = 2.929s, Frame 413)`: `beamng.log` records `reloadResource [.../far_15_1_5_1.dds]` $\to$ **Frame 413** spikes `FileWatchers = 7.39 ms`, `RenderShadows = 11.34 ms` (`FT_next = 19.54 ms`).
  - `t_log = 204.624s (t_cap = 3.594s, Frame 494)`: `beamng.log` records `reloadResource [.../far_15_3_3_-3.dds]` $\to$ **Frame 494** spikes to **`FT = 21.93 ms`** (`RenderShadows = 9.57 ms`, `FileWatchers = 5.07 ms`).
  - `t_log = 205.868s (t_cap = 4.838s, Frames 646–650)`: `beamng.log` records `reloadResource [.../far_15_1_4_-3.dds]` $\to$ **Frames 646–650** suffer a 5-frame hitch cluster (**`22.26 ms, 20.43 ms, 19.86 ms, 27.63 ms, 31.11 ms`**) with `FileWatchers = 2.56–6.88 ms` and `RenderShadows = 9.80–11.81 ms`.
  - `t_log = 209.031s (t_cap = 8.001s, Frames 1096–1105)`: `tunnel_15_6_-4.cdae` and `tunnel_15_6_-3.cdae` written to `<userpath>/temp` $\to$ **Frames 1099–1105** spike to **`23.65 ms, 21.71 ms, 30.75 ms, 20.56 ms, 24.86 ms`** (`FileWatchers = 4.73–9.12 ms`, `RenderShadows = 10.44–11.33 ms`).
  - `t_log = 217.581s..217.722s (t_cap = 16.55s..16.69s, Frames 2343–2354)`: `tunnel_15_1_-6.cdae` through `4_-6.cdae` written to `<userpath>/temp` $\to$ **Frames 2343, 2348, 2354** spike to **`22.76 ms, 20.55 ms, 28.59 ms`** (`FileWatchers = 3.91–5.29 ms`, `RenderShadows = 8.10–17.70 ms`).
  - `t_log = 224.212s (t_cap = 23.182s, Frames 3198–3200)`: `beamng.log` records `reloadResource [.../far_15_0_0_-6.dds]` $\to$ **Frames 3198–3200** spike `FileWatchers = 6.22 ms, 2.38 ms, 2.83 ms` and `RenderShadows = 8.82–9.81 ms` (`FT = 18.96 ms, 18.41 ms`).
  - `t_log = 227.434s..228.937s (t_cap = 26.40s..27.91s, Frames 3645–3801)`: `tunnel_15_-2_*.cdae` and `hm_15_512_-640_178.ter` written to `<userpath>/temp` $\to$ **Frame 3655** (`FileWatchers = 14.13 ms`, `RenderShadows = 13.10 ms`, `FT = 27.77 ms`) and **Frame 3801** (`FileWatchers = 21.62 ms`, `RenderShadows = 9.41 ms`, `FT = 29.61 ms`).
- **Root Cause:** Whenever `earthd` writes or overwrites `.dds`, `.cdae`, `.png`, or `.ter` files inside `<userpath>/temp/beamngEarth/...` (including reusing `far_15_*.dds` filenames or `slot_*.cdae` pool slots), Windows `ReadDirectoryChangesW` notifies Torque3D's C++ `FileWatchers` on the main thread, which performs synchronous NTFS `stat` / resource reloading before Lua's `_G.onFileChanged` filter is ever reached. Typically, a `FileWatchers` stall of `5–14 ms` compounds with an `8–13 ms` `RenderShadows` rebuild in the exact same frame to push total frametime to `20–31 ms`.

#### Bottleneck #3: `FramePresent` D3D12 Swapchain Stalls (15 of 61 Hitches — 24.6%)
- **Observed Spikes:** `FramePresent` spiked to **45.00 ms** (`Frame 1564` $\to$ `FT = 51.78 ms` at `F1565`), **37.32 ms** (`Frame 3454` $\to$ `FT = 44.46 ms` at `F3455`), **27.65 ms** (`F1555` $\to$ `FT = 31.97 ms`), **26.68 ms** (`F1707` $\to$ `FT = 31.88 ms`), **25.52 ms** (`F3763` $\to$ `FT = 30.55 ms`), and **14.29–22.54 ms** across 10 additional frames.
- **Root Cause:** D3D12 `Present()` blocking on the DXGI swapchain / Windows DWM compositor backbuffer flip (exacerbated by multi-viewport ImGui / secondary window swapchains with `vsync=false`, as seen in `beamng.log`: `GFXd3d12WindowTarget::init begin: size=363x898 vsync=false usesSwapChain=true`), plus D3D12 command queue synchronization after heavy resource uploads.

#### Bottleneck #4: `RenderMisc` D3D12 Resource / Terrain Binding Stalls (2 of 61 Hitches — 3.3%)
- **Observed Spikes:**
  - `Frame 1911 (t=13.77s, log=214.80s)`: `RenderMisc = 18.99 ms` ($\to$ `FT = 23.75 ms` at `F1912`).
  - `Frame 3730 (t=27.47s, log=228.50s)`: `RenderMisc = 24.46 ms` ($\to$ `FT = 30.87 ms` at `F3731`), occurring **4 frames (50 ms) before** `beamng.log` logged `addTerrainBlock hm_15_512_-640_178.ter` / `terrain block now at (512, -640), 7.3 ms` at `Frame 3734` (`t=27.53s`), and followed at `Frame 3740` by a `+14.73 MB` physical memory allocation.
- **Root Cause:** Synchronous D3D12 texture/buffer creation and shader resource view binding on the main thread when a new `.ter` terrain block (`hm_15_512_-640_178.ter`) or large satellite DDS batch is imported into the scene.

#### Bottleneck #5: `OtherRender` Forest / Scene Prep Stalls (1 of 61 Hitches — 1.6%)
- **Observed Spike:** `Frame 503 (t=3.67s)`: `OtherRender = 19.20 ms` ($\to$ `FT = 24.74 ms` at `F504`), plus one secondary spike at `Frame 1556 (t=11.20s)` where `OtherRender = 9.71 ms` compounded with `FramePresent`.
- **Root Cause:** `TSForest` render image preparation and instance buffer updates (`Forest::prepRenderImage`) after a burst of tree placements.

---

## 5. Complete Table of All 61 Hitch Frames ($> 20.0\text{ ms}$)

| # | Frame | $t_{\text{cap}}$ (s) | $t_{\text{log}}$ (s) | Frametime (FPS) | CPU Stall Frame | Primary Category | Top CPU Subsystems in Stall Frame |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| 1 | **F258** | 1.63s | 202.66s | 20.63 ms (48.5) | F257 | `RenderShadows` | `RenderShadows=15.11`, `Render=1.84`, `UIimgui=0.61`, `Lua=0.55` |
| 2 | **F331** | 2.15s | 203.18s | 21.41 ms (46.7) | F330 | `RenderShadows` | `RenderShadows=12.76`, `Render=1.78`, `Lua=0.78`, `RenderMisc=0.65` |
| 3 | **F337** | 2.23s | 203.26s | 20.39 ms (49.0) | F337 | `RenderShadows` + `Lua` | `RenderShadows=9.53`, `Lua=5.39`, `Render=1.54`, `RenderMisc=0.74` |
| 4 | **F343** | 2.33s | 203.36s | 23.01 ms (43.5) | F343 | `RenderShadows` + `FileWatchers` | `RenderShadows=8.95`, `FileWatchers=6.79`, `Lua=1.39`, `Render=1.27` |
| 5 | **F377** | 2.63s | 203.66s | 21.84 ms (45.8) | F376 | `RenderShadows` | `RenderShadows=10.25`, `Lua=1.64`, `Render=1.47`, `UIimgui=0.66` |
| 6 | **F395** | 2.77s | 203.80s | 21.33 ms (46.9) | F394 | `RenderShadows` + `FileWatchers` | `RenderShadows=9.99`, `FileWatchers=7.40`, `Lua=2.72`, `Render=2.03` |
| 7 | **F436** | 3.16s | 204.19s | 22.43 ms (44.6) | F436 | `RenderShadows` + `FileWatchers` | `RenderShadows=9.63`, `FileWatchers=4.21`, `Lua=3.49`, `Ticking=1.73` |
| 8 | **F472** | 3.43s | 204.46s | 22.71 ms (44.0) | F472 | `RenderShadows` + `Lua` | `RenderShadows=9.92`, `Lua=7.41`, `Render=1.69`, `UIimgui=0.67` |
| 9 | **F494** | 3.61s | 204.64s | 21.93 ms (45.6) | F494 | `RenderShadows` + `FileWatchers` | `RenderShadows=9.57`, `FileWatchers=5.07`, `Render=1.56`, `Lua=1.02` |
| 10 | **F504** | 3.69s | 204.72s | 24.74 ms (40.4) | F503 | `OtherRender` | `OtherRender=19.20`, `RenderShadows=1.29`, `Render=1.22`, `UIimgui=0.82` |
| 11 | **F523** | 3.84s | 204.87s | 28.12 ms (35.6) | F522 | `RenderShadows` | `RenderShadows=16.07`, `Lua=3.40`, `Render=2.13`, `UIimgui=0.59` |
| 12 | **F527** | 3.90s | 204.93s | 20.02 ms (49.9) | F526 | `FramePresent` | `FramePresent=15.67`, `Render=1.03`, `Lua=0.76`, `RenderShadows=0.69` |
| 13 | **F611** | 4.49s | 205.52s | 20.69 ms (48.3) | F610 | `RenderShadows` + `Lua` | `RenderShadows=11.18`, `Lua=5.98`, `Render=1.54`, `UIimgui=0.65` |
| 14 | **F630** | 4.62s | 205.65s | 20.17 ms (49.6) | F629 | `RenderShadows` + `FileWatchers` | `RenderShadows=10.87`, `FileWatchers=4.45`, `Render=2.12`, `Lua=1.21` |
| 15 | **F646** | 4.81s | 205.84s | 22.26 ms (44.9) | F646 | `RenderShadows` + `FileWatchers` | `RenderShadows=11.81`, `FileWatchers=6.88`, `Render=1.74`, `Lua=1.15` |
| 16 | **F647** | 4.83s | 205.86s | 20.43 ms (48.9) | F647 | `RenderShadows` | `RenderShadows=10.42`, `FileWatchers=2.56`, `Render=1.61`, `Lua=1.02` |
| 17 | **F649** | 4.88s | 205.91s | 27.63 ms (36.2) | F649 | `RenderShadows` + `FileWatchers` | `RenderShadows=9.80`, `Lua=5.89`, `FileWatchers=4.80`, `Ticking=1.87` |
| 18 | **F650** | 4.91s | 205.94s | 31.11 ms (32.1) | F650 | `Lua` + `RenderShadows` | `Lua=11.15`, `RenderShadows=10.10`, `FileWatchers=3.10`, `RenderMisc=3.02` |
| 19 | **F668** | 5.14s | 206.17s | **64.37 ms (15.5)** | F667 | `RenderShadows` | `RenderShadows=58.75`, `Lua=3.16`, `Render=1.45`, `UIimgui=0.64` |
| 20 | **F866** | 6.41s | 207.44s | 22.98 ms (43.5) | F865 | `FramePresent` | `FramePresent=18.95`, `Render=0.93`, `RenderShadows=0.64`, `UIimgui=0.57` |
| 21 | **F1045** | 7.54s | 208.57s | 23.26 ms (43.0) | F1044 | `RenderShadows` | `RenderShadows=17.10`, `Ticking=1.57`, `Render=1.49`, `Lua=0.78` |
| 22 | **F1057** | 7.67s | 208.70s | 24.07 ms (41.5) | F1057 | `RenderShadows` + `FileWatchers` | `RenderShadows=8.90`, `FileWatchers=7.59`, `Render=1.43`, `Lua=0.82` |
| 23 | **F1068** | 7.81s | 208.84s | 20.46 ms (48.9) | F1067 | `RenderShadows` + `FileWatchers` | `RenderShadows=9.37`, `FileWatchers=4.84`, `Render=2.01`, `Lua=0.82` |
| 24 | **F1096** | 8.05s | 209.08s | 21.88 ms (45.7) | F1095 | `RenderShadows` | `RenderShadows=10.48`, `Lua=2.20`, `Render=1.64`, `RenderReflections=0.84` |
| 25 | **F1099** | 8.09s | 209.12s | 23.65 ms (42.3) | F1099 | `RenderShadows` + `Lua` | `RenderShadows=10.75`, `Lua=7.93`, `Render=1.66`, `UIimgui=0.79` |
| 26 | **F1101** | 8.13s | 209.16s | 21.71 ms (46.1) | F1101 | `RenderShadows` + `FileWatchers` | `RenderShadows=10.98`, `FileWatchers=4.73`, `Render=1.61`, `Lua=1.36` |
| 27 | **F1102** | 8.16s | 209.19s | 30.75 ms (32.5) | F1102 | `RenderShadows` + `FileWatchers` | `RenderShadows=11.33`, `FileWatchers=8.49`, `Lua=6.55`, `Render=1.71` |
| 28 | **F1103** | 8.18s | 209.21s | 20.56 ms (48.6) | F1103 | `RenderShadows` | `RenderShadows=11.11`, `FileWatchers=2.58`, `Render=1.64`, `Lua=1.38` |
| 29 | **F1105** | 8.23s | 209.26s | 24.86 ms (40.2) | F1105 | `RenderShadows` + `FileWatchers` | `RenderShadows=10.44`, `FileWatchers=9.12`, `Render=1.72`, `Lua=1.04` |
| 30 | **F1170** | 8.69s | 209.72s | 26.23 ms (38.1) | F1169 | `FramePresent` | `FramePresent=21.03`, `Render=1.48`, `RenderShadows=0.69`, `OtherRender=0.67` |
| 31 | **F1556** | 11.20s | 212.23s | 31.97 ms (31.3) | F1555 | `FramePresent` | `FramePresent=27.65`, `Render=1.31`, `RenderShadows=0.65`, `UIimgui=0.57` |
| 32 | **F1565** | 11.33s | 212.36s | **51.78 ms (19.3)** | F1564 | `FramePresent` | `FramePresent=45.00`, `RenderReflections=1.75`, `Render=1.20`, `RenderShadows=1.11` |
| 33 | **F1708** | 12.50s | 213.53s | 31.88 ms (31.4) | F1707 | `FramePresent` | `FramePresent=26.68`, `Render=1.40`, `RenderShadows=0.95`, `UIimgui=0.80` |
| 34 | **F1912** | 13.79s | 214.82s | 23.75 ms (42.1) | F1911 | `RenderMisc` | `RenderMisc=18.99`, `Render=1.68`, `RenderShadows=0.72`, `UIimgui=0.59` |
| 35 | **F1940** | 13.99s | 215.02s | 28.72 ms (34.8) | F1940 | `Lua` + `LuaGC` | `Lua=23.80`, `LuaGC=6.84`, `Render=1.07`, `RenderShadows=0.74` |
| 36 | **F2020** | 14.48s | 215.51s | 20.26 ms (49.4) | F2019 | `RenderShadows` | `RenderShadows=12.42`, `UImsgLoop=1.83`, `Render=1.56`, `Lua=1.25` |
| 37 | **F2342** | 16.51s | 217.54s | 20.23 ms (49.4) | F2341 | `FramePresent` | `FramePresent=14.74`, `Render=1.15`, `RenderShadows=0.94`, `Lua=0.71` |
| 38 | **F2343** | 16.53s | 217.56s | 22.76 ms (43.9) | F2343 | `RenderShadows` + `Lua` | `RenderShadows=9.41`, `Lua=6.46`, `Render=1.71`, `UIimgui=0.75` |
| 39 | **F2348** | 16.62s | 217.65s | 20.55 ms (48.7) | F2348 | `RenderShadows` + `FileWatchers` | `RenderShadows=8.10`, `FileWatchers=4.21`, `Lua=3.45`, `Render=1.50` |
| 40 | **F2354** | 16.72s | 217.75s | 28.59 ms (35.0) | F2353 | `RenderShadows` | `RenderShadows=17.70`, `FileWatchers=3.91`, `Render=1.48`, `Lua=0.93` |
| 41 | **F2403** | 17.05s | 218.08s | 21.53 ms (46.5) | F2402 | `FramePresent` | `FramePresent=16.61`, `Render=1.31`, `Lua=1.28`, `RenderShadows=0.78` |
| 42 | **F2645** | 18.79s | 219.82s | 22.46 ms (44.5) | F2644 | `FramePresent` | `FramePresent=17.14`, `Render=1.23`, `Lua=0.94`, `RenderShadows=0.69` |
| 43 | **F2848** | 20.32s | 221.35s | 27.52 ms (36.3) | F2847 | `FramePresent` | `FramePresent=22.05`, `Render=1.27`, `OtherRender=1.08`, `RenderShadows=0.68` |
| 44 | **F3079** | 22.05s | 223.08s | 20.39 ms (49.0) | F3078 | `FramePresent` | `FramePresent=15.03`, `Render=1.54`, `RenderShadows=0.96`, `UIimgui=0.61` |
| 45 | **F3141** | 22.50s | 223.53s | 20.80 ms (48.1) | F3140 | `RenderShadows` + `Lua` | `RenderShadows=14.00`, `Lua=4.24`, `Render=1.93`, `Ticking=1.16` |
| 46 | **F3166** | 22.77s | 223.80s | 21.11 ms (47.4) | F3165 | `RenderShadows` | `RenderShadows=10.05`, `FileWatchers=2.79`, `Render=1.83`, `Ticking=1.36` |
| 47 | **F3183** | 22.98s | 224.01s | 20.06 ms (49.8) | F3182 | `RenderShadows` | `RenderShadows=11.65`, `Render=1.88`, `Lua=0.98`, `UIimgui=0.69` |
| 48 | **F3406** | 24.71s | 225.74s | 22.41 ms (44.6) | F3405 | `RenderShadows` | `RenderShadows=15.65`, `Render=1.78`, `Ticking=1.43`, `UIimgui=0.73` |
| 49 | **F3417** | 24.80s | 225.83s | 20.34 ms (49.2) | F3416 | `FramePresent` | `FramePresent=14.29`, `Render=1.47`, `RenderShadows=0.91`, `Ticking=0.73` |
| 50 | **F3455** | 25.12s | 226.15s | **44.46 ms (22.5)** | F3454 | `FramePresent` | `FramePresent=37.32`, `Render=1.54`, `RenderShadows=1.48`, `RenderMisc=0.99` |
| 51 | **F3552** | 25.90s | 226.93s | 21.06 ms (47.5) | F3552 | `RenderShadows` + `FileWatchers` | `FileWatchers=13.08`, `RenderShadows=8.91`, `Render=2.07`, `UImsgLoop=1.00` |
| 52 | **F3645** | 26.66s | 227.69s | 22.74 ms (44.0) | F3644 | `RenderShadows` + `Lua` | `RenderShadows=8.82`, `Lua=6.22`, `UImsgLoop=1.87`, `Render=1.61` |
| 53 | **F3647** | 26.70s | 227.73s | 23.55 ms (42.5) | F3647 | `Lua` + `RenderShadows` | `Lua=10.95`, `RenderShadows=7.81`, `Render=1.35`, `UIimgui=0.65` |
| 54 | **F3654** | 26.80s | 227.83s | 20.64 ms (48.5) | F3653 | `RenderShadows` + `FileWatchers` | `RenderShadows=8.06`, `FileWatchers=7.85`, `Render=1.55`, `Lua=0.69` |
| 55 | **F3655** | 26.82s | 227.85s | 27.77 ms (36.0) | F3655 | `RenderShadows` + `FileWatchers` | `FileWatchers=14.13`, `RenderShadows=13.10`, `Render=1.52`, `Lua=1.16` |
| 56 | **F3656** | 26.85s | 227.88s | 22.21 ms (45.0) | F3656 | `RenderShadows` | `RenderShadows=7.49`, `FileWatchers=2.65`, `Render=1.43`, `Lua=1.11` |
| 57 | **F3731** | 27.50s | 228.53s | 30.87 ms (32.4) | F3730 | `RenderMisc` | `RenderMisc=24.46`, `FramePresent=2.30`, `Render=0.99`, `UIimgui=0.73` |
| 58 | **F3764** | 27.82s | 228.85s | 30.55 ms (32.7) | F3763 | `FramePresent` | `FramePresent=25.52`, `Lua=1.75`, `Render=1.20`, `RenderShadows=0.71` |
| 59 | **F3791** | 28.06s | 229.09s | 20.07 ms (49.8) | F3790 | `RenderShadows` | `RenderShadows=12.65`, `Lua=1.79`, `Render=1.56`, `LuaGC=1.31` |
| 60 | **F3801** | 28.18s | 229.21s | 29.61 ms (33.8) | F3801 | `RenderShadows` + `FileWatchers` | `FileWatchers=21.62`, `RenderShadows=9.41`, `Render=1.75`, `Lua=0.81` |
| 61 | **F4022** | 29.99s | 231.02s | 28.94 ms (34.5) | F4021 | `FramePresent` | `FramePresent=22.54`, `Render=1.40`, `OtherRender=1.33`, `Lua=0.81` |

---

## 6. Actionable Engineering Recommendations for Remaining Bottlenecks

1. **Eliminate `RenderShadows` Cascade Re-Indexing Spikes (Involved in 65.6% of Hitches):**
   - Set `castShadows = false` on farfield terrain meshes (`farfield.lua`), distant building footprint meshes (`bldfar_*`), and tunnel interior meshes (`tunnel_*`). Farfield tiles sit hundreds to thousands of meters away and do not need to invalidate and re-render cascaded shadow maps on every tile swap.
2. **Eliminate C++ `FileWatchers` & `ResourceManager::reloadResource` Stalls (Involved in 27.9% of Hitches):**
   - Stage master `.cdae` and `.dds` generation outside `<userpath>/temp/` before linking, and avoid overwriting active `far_<anchor>_*.dds` or `slot_*.cdae` filenames in-place while registered in `ResourceManager`.
3. **Cap Pre-Governor Inbound IPC Deserialization (`net.lua` / `core.lua`):**
   - Time-slice `net.update()` message popping and `jsonDecode` (e.g., max `0.5–1.0 ms` per frame) and fix the $O(M \cdot B)$ string slice copy in `framing.lua` (`Reassembler:pop()`) so multi-tile server bursts cannot cause `10–23.8 ms` `Lua` decode spikes (`F650`, `F1940`, `F3647`).
