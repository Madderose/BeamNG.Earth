# Phase 10 Wave 1 — W3 (`trees.lua` & `test_trees.lua`) Implementation Report

## 1. Changes Implemented (`file:line`)

### [trees.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua)
- **[trees.lua:67-72](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L67-L72)**: Added `M.MAX_FORESTS_PER_FRAME = 2`, `M.SOLID_SHADOW_NULL_PX = 35`, and `M.NONSOLID_SHADOW_NULL_PX = 150`.
- **[trees.lua:204-250](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L204-L250)**:
  - Removed Wave 2 `2×2` super-tile consolidation (`superForests`, `forestUsers`, `M.SUPER_TILE`, `M.superKey`) and restored per-tile `Forest` ownership from `HEAD`.
  - Kept pooled-`Forest` hiding from P10-D2 via `forestHidden` state table and `setForestHidden(id, f, hidden)` so `f:setHidden(true)` is called in `releaseForest(t)` and `f:setHidden(false)` is called in `forest(t)` **only when the hidden state actually transitions** (O(1), zero scenetree scans).
- **[trees.lua:271-285](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L271-L285)** (R2): Updated `itemType(shape, solid)` so solid/collidable datablocks (`collidable = '1'`) receive `shadowNullDetailSize = '35'` (`M.SOLID_SHADOW_NULL_PX`) and non-solid datablocks (`_n` suffix, `collidable = '0'`) receive `shadowNullDetailSize = '150'` (`M.NONSOLID_SHADOW_NULL_PX`).
- **[trees.lua:421-469](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L421-L469)** (R5 / P10-B):
  - Added module-level `touchedForests` and `touchedForestCount`, cleared in-place in `resetTouched()`.
  - Added `allowForest(t, maxForests, bypassCap)` and `noteForestTouched(t)` updating `M.lastForestsTouched` immediately.
  - Hoisted the per-tile `data()` closure to module-level `tileForestData(t, fd)` (zero per-tile closure allocation).
  - Added lazy-cached `shadowctl` upvalue and `notifyShadowBurst()` (`pcall(require, 'beamngEarth/shadowctl')` resolved at most once, guarded for offline tests).
- **[trees.lua:520-622](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L520-L622), [trees.lua:698-719](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L698-L719)**: Removed `skey` fields in `M.onBin` / `M.onRows` and `movedForestsScratch` in `M.transform`, restoring `HEAD` transform behavior.
- **[trees.lua:786-880](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L786-L880)**:
  - Extended `acquireOrderEntry` with `o[9] = nearSolid` (`dCar <= M.SOLID_M`).
  - Set `maxForests = (gov.burst and not gov.urgent and 1) or M.MAX_FORESTS_PER_FRAME or 2` in governed mode (urgent mode always gets the normal cap of `2`, never `1`).
  - Called `notifyShadowBurst()` inside `finish()` at most once per `M.update()` call when `touchedForestCount > 0`.
- **[trees.lua:882-959](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L882-L959)**: Updated `drainDrops(limit)` to batch removals for one dropped `Forest` at a time in governed mode (`perTile = governed and limit or ...`) and respect `allowForest(t, maxForests, false)`.
- **[trees.lua:981-1129](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L981-L1129)**:
  - Replaced `goto` statements with structured `if/else` blocks.
  - Enforced `allowForest(t, maxForests, nearSolid)` so near-solid tiles (`dCar <= M.SOLID_M`) bypass the Forest cap while non-solid tiles respect it.
  - Removed dead `isRenderShadowEnabled` dynamic field writes and per-tile `require('beamngEarth/shadowctl').onForestTileUpdated(...)` calls.
- **[trees.lua:1138-1174](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua#L1138-L1174)**: Cleaned up `M.clear()` and `M.reset()` (`forestHidden = {}`, `frameN = 0`).

### [test_trees.lua](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_trees.lua)
- **[test_trees.lua:78-80](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_trees.lua#L78-L80), [test_trees.lua:93-95](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_trees.lua#L93-L95)**: Kept pooled `Forest` hidden/unhidden assertions; removed Wave 2 `superKey` / `2×2` super-tile tests.
- **[test_trees.lua:200-214](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_trees.lua#L200-L214)**: Added test verifying solid `TSForestItemData` datablock gets `shadowNullDetailSize == '35'` and non-solid gets `'150'`.
- **[test_trees.lua:216-288](file:///C:/Users/hoppj/SynologyDrive/01_Projets/Projet_BeamEarth/BeamNG.Earth/mod/tests/test_trees.lua#L216-L288)**: Added tests verifying:
  - `govStub` with `burst=true, urgent=false` mutates at most `1` distinct `Forest` per update.
  - `govStub` with `burst=true, urgent=true` mutates up to `2` distinct `Forest`s per update.
  - Near-solid tiles (`dCar <= M.SOLID_M`) bypass the `burst=1` cap.
  - `shadowctl.noteBurst()` is called once per frame when `Forest` mutations occur and `0` times when no `Forest` is mutated.

---

## 2. Test Summary

Command executed:
```powershell
Push-Location mod/tests; ..\..\vendor\luajit\luajit.exe test_trees.lua; Pop-Location
```
Output:
```text
FAIL: far: the fifth with the lowest ranks, the same trees
FAIL: beyond 700 m: 35 %
FAIL: just beyond SOLID_M: still solid (hysteresis)
FAIL: neighbouring tiles: different variants
test_trees: 46 passed, 4 failed
```
- **46 passed, 4 failed** (the exact 4 pre-existing baseline failures listed in `scratch/p10w1_baseline_lua_failures.txt`; zero regressions or crashes).

---

## 3. Risks & Mitigations
- **Near-car tree collision responsiveness**: Mitigated by passing `nearSolid = (dCar <= M.SOLID_M)` into `allowForest(t, maxForests, nearSolid)` so near-car solid tiles always bypass the per-frame `Forest` cap, and urgent governor frames always allow `MAX_FORESTS_PER_FRAME = 2`.
- **Hot-path allocations**: Eliminated per-tile closure allocation (`tileForestData` hoisted to module scope), cached `shadowctl` in a module upvalue, and cleared `touchedForests` in-place.

---

## 4. Cross-Task Requests
- **None** (`trees.lua` calls `shadowctl.noteBurst()` matching W2's interface contract and reads `gov.burst` / `gov.urgent` matching W1's interface contract).
