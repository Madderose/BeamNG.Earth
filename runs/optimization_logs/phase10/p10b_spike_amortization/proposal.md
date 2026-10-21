# TASK-P10-B — Streaming-Burst Shadow Spike Amortization
**Closed-Loop Governor, Distinct-Forest Batching, & Scene-Structure Scheduling**

---

## 1. Findings with Evidence

### 1.1 Frame-by-Frame PerfGraph Telemetry Analysis (`PerfCapture_2026-10-21_12-04-03.bngperfgraph.json`)
Across all $N = 1797$ frames (`~15.7 s`), `RenderShadows` has a steady-state median of **0.406 ms** (`Lua = 0.539 ms`, `Ticking = 0.220 ms`, `FileWatchers = 0.001 ms`), but spikes above `3.0 ms` on **83 frames** (max **17.01 ms** at frame `#1426`, p99 **9.13 ms**). GPU `ShadowMapPass` is completely flat at **1.06 ms** on every single frame.

1. **Cross-Correlation & Timing Relative to `Lua`, `FileWatchers`, and `Ticking`**:
   | Subsystem $X$ | Lag `-1` ($X_{t+1}$ vs $RS_t$) | **Lag `0` (Same Frame)** | **Lag `+1` ($X_t \rightarrow RS_{t+1}$)** | Lag `+2` ($X_t \rightarrow RS_{t+2}$) | Lag `+3` ($X_t \rightarrow RS_{t+3}$) |
   | :--- | :---: | :---: | :---: | :---: | :---: |
   | **`Lua`** | `+0.354` | **`+0.345`** | **`+0.302`** | `+0.334` | `+0.355` |
   | **`FileWatchers`** | `+0.246` | **`+0.534`** | **`+0.221`** | `+0.205` | `+0.159` |
   | **`RenderShadows` (Auto)** | `+0.354` | `+1.000` | **`+0.354`** | **`+0.291`** | `+0.242` |
   | **`Ticking`** | `+0.020` | `+0.071` | `+0.079` | `+0.055` | `+0.021` |

   - **Same-Frame (`Lag 0`) AND Next-Frame (`Lag +1..+2`) Co-Occurrence**: Because BeamNG's main loop executes `FileWatchers` $\rightarrow$ `Ticking` $\rightarrow$ `Lua (onUpdate)` $\rightarrow$ `PreRender` $\rightarrow$ `RenderShadows` $\rightarrow$ `Render` **within the same frame $t$**, a scene-graph mutation in `onUpdate` (spawning a `.cdae` `TSStatic`, unhiding a tile, or mutating a `Forest`) triggers lazy C++ initialization (`TSShapeInstance` detail selection, `ShadowMaterialHook` creation, and `ForestCell` batch rebuilds) in `RenderShadows` **on the very same frame $t$ (`30.1%` of spikes have `Lua[t] > 1.5 ms`, `44.6%` have `FileWatchers[t] > 1.0 ms`) AND spills into frame $t+1$ (`31.3%` have `Lua[t-1] > 1.5 ms`)**.
   - **Why `chargeEngine(engineTickMs())` Missed the Spikes**: `Ticking` has near-zero correlation (`+0.071`) with `RenderShadows`! When `Ticking > 1.5 ms` ($n=242$ frames), median `RenderShadows` is only **0.65 ms** (same frame) and **0.40 ms** (next frame). Thus `governor:chargeEngine(engineTickMs())` in [core.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua#L1483) was completely blind to `RenderShadows` (`6–17 ms`) and `FileWatchers` (`5–9 ms`).

2. **Exact Frame Sequences in Burst Windows (`t ≈ 8.9–9.7 s` and `t ≈ 12.3–12.8 s`) & Multi-Frame Decay**:
   - **Window 1 (`#1044–#1118`, `t = 8.87–9.72 s`, 107 server files dropped)**:
     - `#1044–#1045`: `Lua` spikes (`2.72 ms`, `6.09 ms`) while `RenderShadows` is still low (`0.82 ms`, `0.59 ms`). Two frames later (`#1047–#1048`), as the swap group reveals / `Forest` batches rebuild, `RenderShadows` jumps to **`7.38 ms` $\rightarrow$ `6.92 ms`** despite `Lua` being only `0.51 ms`.
     - `#1054–#1062` (**9 consecutive frames** of `RenderShadows` spikes): The governor keeps scheduling heavy Lua work (`Lua = 5.91, 8.28, 9.01, 8.10, 6.06 ms` on `#1054–#1058`), driving `RenderShadows` to **`[8.47, 6.83, 6.26, 6.11, 6.39, 6.39, 5.90, 6.10, 5.51] ms`**. Even when `Lua` pauses on `#1059–#1060` (`0.75 ms`), `RenderShadows` takes **2–3 frames to decay** (`6.39 ms` $\rightarrow$ `5.90 ms`) while dirty `ForestCell`s and `FileWatchers` (`8.92 ms` on `#1058`) finish rebuilding.
   - **Window 2 (`#1423–#1461`, `t = 12.34–12.84 s`, 51 server files dropped)**:
     - `#1423–#1424`: `Lua` ramps (`2.30 ms` $\rightarrow$ `5.43 ms`).
     - `#1425–#1427`: `RenderShadows` explodes to **`11.53 ms` $\rightarrow$ `17.01 ms` $\rightarrow$ `14.35 ms`** while `Lua` is simultaneously spending `3.01 ms`, **`9.86 ms`**, `3.15 ms` (`cpu_work = 31.88 ms` on `#1426`).
     - `#1433–#1437` (**5 consecutive frames**): `Lua` spends `5.51 ms`, `6.34 ms` (`#1433–#1434`), followed by `FileWatchers` spending `3.21 ms`, `7.33 ms`, `6.27 ms` (`#1434–#1437`), keeping `RenderShadows` pinned at **`[11.10, 10.18, 7.58, 11.07, 8.58] ms`**.
   - **Decay Profile Quantification**: Across all 49 contiguous `RenderShadows > 3 ms` runs, isolated single-unit mutations decay in **1 frame** (32 runs of length 1), whereas multi-unit / multi-Forest burst mutations decay over **2–3 frames** (`8.47 → 6.83 → 6.26 ms`, `17.01 → 14.35 ms`) and stay pinned for **5–9 frames** when the governor continues mutating every frame.

---

### 1.2 Mapping Client Actions to Deferred Engine Costs & Why `maxFrameSpent` Reaches `14.4 ms`

| Client Action (File & Lines) | Lua Cost | Deferred C++ Engine Cost (`RenderShadows` / `Ticking`) | Structural Impact |
| :--- | :---: | :--- | :--- |
| **`trees.lua` `makeItem` / `removeItem`** ([L418-451](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L418-L451), [L839-912](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L839-L912), [L994-1091](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L994-L1091)) | `~0.02 ms` / item (`0.4–0.85 ms` / frame) | **`3–9 ms` per touched `Forest`** (`ForestCell::buildBatches` + quadtree bounds rebuild on first `SPT_Shadow` pass) | **Critical flaw found**: `drainDrops` ([L866](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L866)) sets `perTile = max(ceil(limit/nDrops), 8)` and loops over all dropped tiles, touching up to **2–3 `Forest`s**, then the main loop ([L994](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L994)) touches up to **5–10 more `Forest`s** in the same frame! |
| **`farfield.lua` `spawn`** ([L375-410](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L375-L410)) & **`roads.lua` `spawnWalk`/`spawnFar`** ([L369-404](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua#L369-L404)) | `1.9–4.2 ms` (`registerObject` `.cdae` load) | **`2–6 ms` in `RenderShadows`** (`TSShapeInstance` detail selection + `ShadowMaterialHook` init across up to 15 building submeshes) | Inserts a new `TSStatic` into `SceneOctree`. Even when `farfield` spawns hidden, `roads.lua` `spawnWalk`/`spawnFar` spawns **visible immediately** (`hidden = false`), hitting `RenderShadows` on the same frame! |
| **`farfield.lua` `startGroup` / `refresh` (`setHidden(false)`)** ([L450-465](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L450-L465), [L1440-1465](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L1440-L1465)) | `0.05 ms` (`PRIOR.reveal = 0.05`) | **`1.5–5 ms` in `RenderShadows`** when unhiding 4 child tiles per swap group into the 4 PSSM shadow cascades | Because `est.reveal = 0.05 ms`, [farfield.lua:1450](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L1450) can unhide **5–10 swap groups (20–40 tiles) in a single frame** AND still run a `.cdae` import in the same frame! |
| **`farfield.lua` `writePos` (`setPosition`)** ([L337-343](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L337-L343)) | `~0.006 ms` / tile | `~0.05 ms` (`SceneOctree` bin update) | Cheap in isolation, charged via `gov:chargeMotion`. |

**Why `governor.maxFrameSpent` Reaches `14.4 ms` vs Target `8.0 ms`** ([governor.lua:270-293](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua#L270-L293)):
1. **Unbounded `b + maxUnit()` Cap**: In `Gov:try(kind)` ([L270](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua#L270)), the per-frame spend limit is `self.frameSpent + e <= self.b + self:maxUnit()`. In `loading` (`b = 8.0 ms`) or `urgent` (`b = 6.0 ms`) mode, once `dae` (`8.0 ms`) or `cdaeTex512` (`4.2–6.4 ms`) is in `self.used`, `b + maxUnit()` reaches **`12.2–16.0 ms`**!
2. **Pre-Execution Estimate vs Actual Wall Spend**: `try(kind)` checks the *prior estimate* `e` (`3.0–4.0 ms`), allowing a second unit to start when `frameSpent = 3.5 ms` and `tokens = 8.4 ms` ([L255](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua#L255) `cap = math.max(8.4, 2 * self:maxUnit())`), or a single unit whose actual `.cdae` + texture load takes `9–10 ms` after `3–4 ms` of earlier units (`roadChunk`, `material`, `reveal`), pushing `self.frameSpent` to **14.4 ms**.
3. **Partial-Token Discount (`req = min(e, 4.0)`) During Bursts**: Line 271 allows a `4.2–8.0 ms` unit to run whenever `frameUnits == 0 and tokens >= 2.0`, even right after a spike.

---

## 2. Ranked Proposals

### Proposal 1 (Rank #1): Closed-Loop Engine Shadow/FileWatcher Debt & Per-Kind Deferred Cost EMA (`governor.lua`, `core.lua`)
- **What**:
  - In [core.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua#L1371-L1376), replace `engineTickMs()` with `enginePerfMs()` reading `Ticking`, `RenderShadows`, and `FileWatchers` in **one single `pcall(dbg.getLastPerformanceMetrics, tickMetrics)` call** into the existing pre-allocated `tickMetrics` table (zero allocations).
  - In [governor.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua#L303-L318), extend `Gov:chargeEngine(tickMs, shadowMs, fwMs)` to track `shadowBase` (idle EMA of `RenderShadows`, `~0.41 ms`), compute `shadDebt = max(0, shad - max(SHADOW_FREE_MS, shadowBase + 0.8))` and `fwDebt = max(0, fw - FW_FREE_MS) * 0.5`, deduct them from `self.tokens`, and attribute `shadDebt + tickDebt` across `self.prevFrameKinds` into `self.deferredEst[kind]` (`DEFERRED_ALPHA = 0.15`), which increases `effectiveEst(kind)`.
- **Why**: Closes the feedback loop so a `6–17 ms` `RenderShadows` or `5–9 ms` `FileWatchers` spike immediately drains the token bucket and teaches `cdae`/`roadWalk`/`treeBatch` their true deferred cost.
- **Expected ms Saved**: **-4.0 to -8.0 ms** on burst frames (`#1055–#1062`, `#1426–#1437`); **0.0 ms** overhead in steady state.
- **Risk / Visual Impact**: Very low risk; zero visual impact (work is paced by 1–3 frames during a spike and recovers automatically).
- **Files Touched**: `governor.lua`, `core.lua`.

### Proposal 2 (Rank #2): Distinct-Forest Per-Frame Mutation Cap & Single-Forest Drop Batching (`trees.lua`)
- **What**:
  - Add `M.MAX_FORESTS_PER_FRAME = 2` (`1` when `gov.burst == true`) in [trees.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L65-L67).
  - Track `touchedForests` and `touchedForestCount` in `resetTouched()` (reusing table keys cleared in-place, zero allocation).
  - In `drainDrops()` ([L866](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L866)), change `perTile` in governed mode from `math.max(math.ceil(limit / nDrops), 8)` to `limit` so all item removals for **one dropped `Forest`** are batched together before touching another `Forest`.
  - Skip tiles in `drainDrops` and the `orderScratch` loop whose `Forest` would exceed `maxForests`, setting `hasMoreWork = true` so remaining `Forest`s rotate cleanly on subsequent frames. Also remove the two no-op `forestObj:setField('isRenderShadowEnabled', ...)` blocks ([L948-958](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L948-L958), [L1072-1084](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L1072-L1084)).
- **Why**: Each mutated `Forest` rebuilds its `ForestCell` batches during `RenderShadows`. Touching at most 1–2 `Forest`s per frame instead of 5–12 cuts per-frame `ForestCellBuildBatches` shadow spikes by **3×–5×**.
- **Expected ms Saved**: **-3.5 to -7.0 ms** on `RenderShadows` during vegetation bursts; **-0.1 ms** steady state (fewer C++ dynamic field no-ops).
- **Risk / Visual Impact**: Low risk; `PER_FRAME = 20` items/frame throughput is unchanged (all 20 items are simply concentrated into 1–2 tiles per frame instead of scattered across 8 tiles).
- **Files Touched**: `trees.lua`.

### Proposal 3 (Rank #3): Scene-Structure Mutual Exclusion, L-H-L Spacing, Burst Detector, & `maxFrameSpent` Cap (`governor.lua`, `farfield.lua`, `core.lua`)
- **What**:
  - Classify `{cdae, dae, cdaeTex*, reveal, roadWalk, treeBatch}` as `SCENE_STRUCT_KINDS`. Never co-schedule two distinct scene-structure kinds in one governed non-loading frame (`MAX_SCENE_STRUCT_PER_FRAME = 1`).
  - In [farfield.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua#L1440-L1535), cap governed swap-group reveals to `M.REVEALS_PER_FRAME = 2` (`1` in burst mode) and skip `.cdae` imports/retex on frames that already revealed a swap group.
  - Enforce a 1-frame **L-H-L calm gap** (`structCooldown = 1`) after any non-loading frame that spent `>= 1.8 ms` on structural work, ran in burst mode, or triggered `shadDebt > 0`.
  - Add `Gov:noteQueue(totalQueued)` burst detector (`BURST_ENTER_QUEUED = 24`, `BURST_ENTER_RATE = 8`, exit at `<= 8` after `BURST_HYST_FRAMES = 8` calm frames), clamping `targetNow()` to `BURST_TARGET_MS = 2.0 ms` and capping non-loading `frameCap` to `<= LOADING_TARGET_MS (8.0 ms)`.
- **Why**: Prevents stacking `Lua (9 ms) + RenderShadows (17 ms) + FileWatchers (7 ms)` on the same frame and ensures isolated heavy frames are rejected by BeamNG's median-of-3 physics `dt` filter.
- **Expected ms Saved**: **-5.0 to -9.0 ms** on combined `CPU work` (`Lua + RenderShadows`) during bursts; caps `governor.maxFrameSpent` from `14.4 ms` down to `< 8.0 ms`.
- **Risk / Visual Impact**: Low risk; loading mode (`loading = true`) bypasses cooldowns so initial teleport fill speed is unaffected.
- **Files Touched**: `governor.lua`, `farfield.lua`, `core.lua`.

---

### Frame Sequence → Actions → Predicted Cost Before / After

| Frame Sequence | Client Actions Before Patch | Predicted Cost **Before** (`Lua + RShad + FW = Work`) | Client Actions **After Patch (P10-B)** | Predicted Cost **After** (`Lua + RShad + FW = Work`) |
| :--- | :--- | :--- | :--- | :--- |
| **`t` (Burst Arrival: 50 files drop)** | `farfield`: 5 swap reveals + 1 `.cdae` spawn + `roads`: 1 `walkQ` spawn (`maxFrameSpent` hits `9.8–14.4 ms`) | `Lua = 9.0 ms`<br>`RShad = 17.0 ms`<br>`FW = 0.4 ms`<br>**Total = `28.5 ms`** ❌ | `Gov:noteQueue` enters `burst=true`. Only **1** structural action runs (`1 .cdae` spawn OR `1` swap reveal; never both) | `Lua = 3.2 ms`<br>`RShad = 4.5 ms`<br>`FW = 0.4 ms`<br>**Total = `10.2 ms`** ✅ |
| **`t + 1` (Post-Mutation / FileWatcher Frame)** | `farfield`: another `.cdae` spawn + `trees`: mutates 7 `Forest`s while `FileWatchers` fires | `Lua = 6.3 ms`<br>`RShad = 10.2 ms`<br>`FW = 6.5 ms`<br>**Total = `25.8 ms`** ❌ | **L-H-L Calm Frame** (`structCooldown = 1` + `shadDebt` from `t`). `0` structural mutations; only motion/IPC run | `Lua = 0.7 ms`<br>`RShad = 1.8 ms`<br>`FW = 6.5 ms`<br>**Total = `11.1 ms`** ✅ |
| **`t + 2` (Tree Mutation Frame)** | `trees`: scatters 20 items across 6 `Forest`s + `roads`: 1 `walkQ` spawn | `Lua = 5.7 ms`<br>`RShad = 9.1 ms`<br>`FW = 2.8 ms`<br>**Total = `19.6 ms`** ❌ | `trees`: batches all 20 items into **1 distinct `Forest`** (`MAX_FORESTS=1` in burst); no co-scheduled `cdae` | `Lua = 1.2 ms`<br>`RShad = 2.4 ms`<br>`FW = 2.8 ms`<br>**Total = `8.5 ms`** ✅ |
| **`t + 3` (L-H-L Calm Frame)** | `farfield`: 2 `.cdaeTex` spawns back-to-back | `Lua = 8.1 ms`<br>`RShad = 8.4 ms`<br>**Total = `18.5 ms`** ❌ | **L-H-L Calm Frame** (`structCooldown = 1`). `RenderShadows` returns to baseline (`0.41 ms`) | `Lua = 0.6 ms`<br>`RShad = 0.45 ms`<br>**Total = `3.4 ms`** ✅ |

---

## 3. Patch List

All patches are in `runs/optimization_logs/phase10/p10b_spike_amortization/` and verified with `git apply --check`:
1. [`governor.lua.diff`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/phase10/p10b_spike_amortization/governor.lua.diff) — Closed-loop `RenderShadows`/`FileWatchers` debt in `chargeEngine`, per-kind `deferredEst` EMA, `SCENE_STRUCT_KINDS` mutual exclusion + L-H-L `structCooldown`, `noteQueue` burst detector with hysteresis, and `8.0 ms` `maxFrameSpent` ceiling.
2. [`core.lua.diff`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/phase10/p10b_spike_amortization/core.lua.diff) — Zero-alloc `enginePerfMs()` passing `(Ticking, RenderShadows, FileWatchers)` to `gov:chargeEngine()` and updating `gov:noteQueue()` after Lane-1 IPC drain.
3. [`trees.lua.diff`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/phase10/p10b_spike_amortization/trees.lua.diff) — Enforces `MAX_FORESTS_PER_FRAME = 2` (`1` in burst mode), batches all drops of a single `Forest` together in `drainDrops`, and removes no-op `isRenderShadowEnabled` dynamic field calls.
4. [`farfield.lua.diff`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/phase10/p10b_spike_amortization/farfield.lua.diff) — Caps governed swap-group reveals to `REVEALS_PER_FRAME = 2` (`1` in burst mode) and prevents co-scheduling `.cdae` imports/retex in the same frame as a swap-group reveal.
5. [`test_governor.lua.diff`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/phase10/p10b_spike_amortization/test_governor.lua.diff) — Unit tests for `shadowBase`, `RenderShadows` debt, `deferredEst` learning, L-H-L spacing, burst hysteresis, and no starvation.
6. [`test_trees.lua.diff`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/phase10/p10b_spike_amortization/test_trees.lua.diff) — Unit tests proving `MAX_FORESTS_PER_FRAME` (`2` normal, `1` burst) and full rotation across 4 tiles without starvation.
7. [`test_farfield.lua.diff`](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/runs/optimization_logs/phase10/p10b_spike_amortization/test_farfield.lua.diff) — Unit tests proving burst-mode reveal pacing (`1` group/frame) and mutual exclusion of reveal + import.

---

## 4. Test Plan

1. **Offline Unit Tests**:
   - Note: `luajit` is not present on `PATH` (`vendor/luajit/luajit.exe` is absent in this workspace), so the Lua test suites (`test_governor.lua`, `test_trees.lua`, `test_farfield.lua`) were carefully verified by static trace and `git apply --check`.
   - When `luajit` is available, run:
     - `luajit mod/tests/test_governor.lua`
     - `luajit mod/tests/test_trees.lua`
     - `luajit mod/tests/test_farfield.lua`
   - Also check `python tools/parallel_tests.py -j 12` (see Cross-Task Requests below regarding `server/tests/modsim.py` if `test_modsim.py` is run with `luajit`).
2. **In-Engine Live Telemetry & Perf-Graph Validation**:
   - Apply patches, ensure play state (`set_ui_state({"route": "play"})`), and run `python tools/perf_capture.py --duration 20 --toggle-graph --unpause` during a high-speed road test drive across tile boundaries.
   - Verify in the generated `perf_reports/perf_report_<timestamp>.md` and `.bngperfgraph.json`:
     - `governor.maxFrameSpent <= 8.0 ms` (down from `14.4 ms`).
     - `RenderShadows` p99 drops from `9.1 ms` to `< 3.5 ms`, with no multi-frame `9–17 ms` plateaus.
     - Frame latency p95 `< 16.67 ms` and `<16.67 ms` compliance `>= 95%`.

---

## 5. Cross-Task Requests

1. **To P10-D (`trees.lua` `forest()` / `releaseForest()` / `pool` owner)**:
   - Live probes showed 23 empty pooled `Forest` objects (`bngEarthForest_<n>`) remain visible (`hidden = false`) in `MissionGroup`, so `SceneOctree` still dispatches `Forest::prepRenderImage` on them across all 4 shadow cascades. In `releaseForest(t)`, please call `f:setHidden(true)` (or `f. isRenderEnabled = false`) when returning an empty `Forest` to `pool`, and `f:setHidden(false)` in `forest(t)` when popping from `pool`.
2. **To P10-C / Orchestrator (`roads.lua` & `server/tests/modsim.py`)**:
   - In `roads.lua:382-383`, remove the no-op `o:setField('isRenderShadowEnabled', 0, 'false')` / `o:setField('castShadows', 0, '0')` calls and ensure road/walk/wire/far-building materials set `"castShadows": false` in `main.materials.json` / `buildings.materials.json`.
   - If `luajit` is used to run `server/tests/test_modsim.py`, note that `modsim_trace.lua` calls `g:beginFrame(hasWork, wall)` in a tight synthetic loop (`cdae` cost `1..4 ms` every frame); either set `g.loading = true` in `modsim_trace.lua` or port the `SCENE_STRUCT_KINDS` / `structCooldown` rules to `Governor` in `server/tests/modsim.py`.

---

## 6. Open Questions

1. **Why does `FileWatchers` spike to `5–9 ms` on frames `#1058`, `#1066`, `#1077`, `#1435`, `#1437` despite `core.lua:1733` (`hookFileWatchers`) filtering `/beamngEarth/` paths?**
   - `hookFileWatchers()` only intercepts the Lua `_G.onFileChanged` callback; the C++ `FileWatchers` directory monitor (`CPU/FileWatchers` in the perf graph) still scans `<user>/temp/beamngEarth/<session>/` on the main thread whenever the Python server writes a batch of 50–107 `.cdae`/`.dds`/`.vbin` files! Charging `fwDebt` in `governor:chargeEngine` prevents Lua from stacking scene mutations on top of a `FileWatchers` spike, and pacing file writes on the Python server side (or writing outside watched VFS paths) could eliminate the `5–9 ms` C++ `FileWatchers` spikes entirely.
