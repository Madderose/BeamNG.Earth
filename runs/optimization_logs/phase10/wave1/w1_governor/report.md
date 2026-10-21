# TASK-P10W1-GOV — Wave 1 Implementation Report: Governor R1 Fix & Burst Hardening

## 1. Summary of Changes (`file:line`)

### 1.1 `mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua`
- **Burst Constants & Documentation (`governor.lua:58-69`)**:
  - Documented all Phase 10 constants with one-line rationale comments matching the module's flat-table style (`modsim.py` `lua_consts` compatible).
  - Added `M.BURST_MAX_FRAMES = 90` (~1.5 s at 60 Hz maximum burst duration) and `M.BURST_REFRACTORY_FRAMES = 60` (~1.0 s cooldown after a max-duration burst before burst can re-enter).
- **Instance State Initialization (`governor.lua:117-125`)**:
  - Added `burstActiveFrames = 0`, `burstRefractory = 0`, `prevQueued2 = 0`, `prevQueued3 = 0`, and `maxUnitCached = 0` in `M.new`.
- **Transient Burst Detector (`Gov:noteQueue`, `governor.lua:177-218`)**:
  - Tracks 3-frame queue history (`prevQueued`, `prevQueued2`, `prevQueued3`) with zero allocations.
  - Enters `burst` only when `(self.burstRefractory or 0) == 0` AND (`rate >= M.BURST_ENTER_RATE` OR (`q >= M.BURST_ENTER_QUEUED` and `q` grew over the last 1–3 frames)). A constantly high non-growing queue (e.g. steady `q = 40` at highway speed) does not enter or re-enter burst mode.
  - Preserves low-queue exit hysteresis (`q <= M.BURST_EXIT_QUEUED` for `M.BURST_HYST_FRAMES = 8` frames).
  - Caps continuous burst duration at `M.BURST_MAX_FRAMES = 90` frames, then forces `self.burst = false` and arms `self.burstRefractory = M.BURST_REFRACTORY_FRAMES` (`60` frames), blocking immediate re-entry.
- **R1 Fix — `Gov:targetNow()` Priority (`governor.lua:220-225`)**:
  - Reordered priority to **`loading > urgent > burst > normal`**. When `self.urgent` is true (`core.lua:1026`: `pl.speed > 25` or `underLevel > -1`), `targetNow()` returns `max(self.target, M.URGENT_TARGET_MS)` (`6.0 ms`) instead of clamping to `M.BURST_TARGET_MS` (`2.0 ms`).
- **Hot-Path Zero-Allocation & `maxUnit` Caching (`governor.lua:237-259`, `299-305`, `356-361`, `408-417`)**:
  - Added `recomputeMaxUnit(self)` (`governor.lua:237-245`) called once per frame in `beginFrame` (`governor.lua:305`) and on `charge` if the previous maximum unit estimate shrinks (`governor.lua:414-416`).
  - `Gov:maxUnit()` (`governor.lua:248-250`) now returns `self.maxUnitCached or 0` in $O(1)$ without iterating `self.used`. `Gov:try` updates `maxUnitCached` in $O(1)$ when a newly seen kind is added (`governor.lua:356-360`) and `Gov:charge` updates it in $O(1)$ when an estimate grows (`governor.lua:412-413`).
  - Replaced the per-frame table allocation in `median(t, n)` with module-level `medianScratch` (`governor.lua:252-259`), clearing any stale tail elements in-place before `table.sort(medianScratch)`.
- **R1 Fix — Urgent Exemption from Structural Exclusion & Burst Throttles (`governor.lua:306-312`, `362-383`, `486-490`)**:
  - `Gov:beginFrame` (`governor.lua:308`) and `Gov:chargeEngine` (`governor.lua:488`) do not arm `structCooldown` while `self.urgent` is true.
  - In `Gov:try(kind)` (`governor.lua:362-383`), defined `local burstThrottle = self.burst and not self.urgent`:
    - When `self.urgent` is true, skips `structCooldown` and `MAX_SCENE_STRUCT_PER_FRAME` checks (`governor.lua:364-373`).
    - Uses the normal non-burst frame cap (`M.LOADING_TARGET_MS = 8.0 ms`) instead of `b + min(maxU, 4.5)` (`governor.lua:378`).
    - Preserves the first-unit partial-token discount (`min(e, 4.0)`) when `self.urgent` is true (`governor.lua:382`).
- **`sceneStructCount` Interface Contract (`governor.lua:304`, `404-406`)**:
  - Kept `self.sceneStructCount` semantics unchanged (reset to `0` in `beginFrame`, incremented in `charge` for every `SCENE_STRUCT_KINDS[kind]` unit regardless of `urgent`/`loading`) so `shadowctl.lua` can read it in `onPreRender`.

### 1.2 `mod/tests/test_governor.lua`
- **Sustained Spend Analysis & Fix (`test_governor.lua:56-66`)**:
  - **Root cause of `got 1.5, want 2`**: `frame(g, { cost = 3 })` defaults to `kind = 'cdae'`, which is in `SCENE_STRUCT_KINDS`. At `b = 2.0 ms` and `est.cdae = 3.0 ms`, `frameCap = b + maxUnit = 5.0 ms` allows at most **1** `3 ms` unit per active frame (`3 + 3 = 6 > 5`). Because `3.0 ms >= STRUCT_COOLDOWN_MS (1.8 ms)`, P10-B's L-H-L spacing (`governor.lua:308-311`, required by P10-B test #2 at `test_governor.lua:254`) inserts 1 calm cooldown frame (`structCooldown = 1`) after every active frame, so `cdae` runs on 50 of 100 frames (`50 * 3 ms / 100 = 1.5 ms/frame`).
  - Updated the expectation for `cdae` (`cost = 3`) to `1.5 ms/frame` with an explanatory comment, and added a companion assertion verifying that non-structural units (`kind = 'retex', cost = 3`) continue to spend `~ b = 2.0 ms/frame`.
- **New Wave 1 Unit Tests (`test_governor.lua:292-343`)**:
  - **Test 5 (R1 urgent beats burst)**: Verifies `loading > urgent > burst > normal` in `targetNow()`, proves two structural units (`cdae` + `roadWalk`) can run in a single urgent+burst frame (`sceneStructCount == 2`), and verifies `beginFrame` does not arm `structCooldown` while urgent.
  - **Test 6 (`BURST_MAX_FRAMES` & refractory)**: Verifies burst exits after exactly `BURST_MAX_FRAMES = 90` frames even under continuous queue growth, arms `burstRefractory = 60`, blocks re-entry across all 60 refractory frames despite `+10/frame` surges, and allows re-entry on frame 61.
  - **Test 7 (High non-growing queue)**: Verifies `q = 40` every frame neither enters burst from steady state nor keeps burst on after `BURST_MAX_FRAMES`.

## 2. Test Results

Command executed:
`Push-Location mod/tests; ..\..\vendor\luajit\luajit.exe test_governor.lua; ..\..\vendor\luajit\luajit.exe test_core_stubbed.lua; Pop-Location`

Output summary lines:
```text
FAIL: w1 > 11.0 ms holds b = 0 for 1 cooldown frame
test_governor: 545 passed, 1 failed
FAIL: recent places: the level start recorded
FAIL: default lat: got 36.596718, want 36.5785 (tol 1e-09)
FAIL: default lon: got -118.169991, want -118.2923 (tol 1e-09)
test_core_stubbed: 263 passed, 3 failed
```
*(All 4 failures above are the exact pre-existing baseline failures listed in `scratch/p10w1_baseline_lua_failures.txt`; 0 new failures.)*

## 3. Risks
- **Low Risk — Refractory Window During Back-to-Back Tile Boundary Crossings**: After a 90-frame (`~1.5 s`) burst timeout, `BURST_REFRACTORY_FRAMES = 60` (`~1.0 s`) prevents burst target clamping (`2.0 ms`) from re-engaging immediately, allowing normal token drain while still keeping closed-loop `RenderShadows`/`FileWatchers` debt (`chargeEngine`), single-structural-kind mutual exclusion, and L-H-L `structCooldown` active.

## 4. Cross-Task Requests
- **None** for Wave 1 Lua workers (`shadowctl.lua` and `trees.lua` interface contract fields `gov.burst`, `gov.urgent`, `gov.loading`, `gov.sceneStructCount` are preserved with exact semantics).
- **For Orchestrator (`server/tests/test_modsim.py`)**: Now that `luajit` is installed, if `test_modsim.py` is run during full-suite validation, note that `server/tests/modsim.py`'s `Governor` port reflects the pre-P10-B model (no `SCENE_STRUCT_KINDS` or `structCooldown` in `server/tests/lua/modsim_trace.lua`).

STATUS_UPDATE: DONE (100%)
