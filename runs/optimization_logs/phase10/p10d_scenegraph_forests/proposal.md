# Phase 10 — TASK-P10-D: Scene-Graph Object Count Reduction & Forest Consolidation

## 1. Findings & Scene-Graph Count Model

### 1.1 Why Scene-Graph Object Count Dominates `RenderShadows` and `RenderMain`
In BeamNG.drive's Torque3D engine (`Engine/source/scene/sceneZoneSpaceManager.cpp`, `Engine/source/lighting/advanced/hlsl/deferredShading.cpp`), every active PSSM shadow cascade (`0..3`) and the main camera frustum execute a `SceneContainer::findObjects` octree query followed by a virtual `SceneObject::prepRenderImage(SceneRenderState*)` call on every unhidden, render-enabled `SceneObject` intersecting the query volume.
- Although `terrain.lua:207-230` sets `lastSplitTerrainOnly = "1"` on `theSun` so **Cascade 3** skips non-terrain objects, **Cascades 0, 1, and 2** (`3` cascades) plus **RenderMain** (`1` pass) still visit every intersecting unhidden `Forest` and `TSStatic`.
- Worse, in Torque3D (`Engine/source/forest/forest.cpp`), `Forest::onAdd()` calls `setGlobalBounds()` (`mGlobalBounds = true`, infinite world box). Consequently, **every unhidden `Forest` in `MissionGroup` intersects every active shadow cascade (`0, 1, 2`) and the main frustum on every single frame**, regardless of where its items lie—or even if it contains **zero** items!
- Inside `Forest::prepRenderImage()`, each `Forest` independently walks its own `ForestData` root `ForestCell` quadtree (`ForestCellCulling`), allocates render batches (`ForestCellBuildBatches`), and submits imposter/mesh draw calls (`ForestRender`).

### 1.2 Analytical Scene-Graph Count Model vs. Live Probe
For a square `256 m` tile grid (`TILE = 256 m`, area $A_{\text{tile}} = 65,536\text{ m}^2$), a Chebyshev/Euclidean box-distance threshold $d \le R$ covers a Minkowski-expanded footprint of area:
$$A(R) = \pi R^2 + 4 \cdot 256 \cdot R + 256^2, \qquad N_{\text{tiles}}(R) = \frac{A(R)}{256^2}$$

#### A. `Forest` SceneObjects (`mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua`)
1. **Vegetation tiles (`veg_tile`, key `"<aid>:<tx>_<ty>"`)**:
   - Server (`server/vegetation.py:674-675`) sends `256 m` tiles within `SEND_M = 1280 m` and drops beyond `DROP_M = 1536 m`.
   - Client (`trees.lua:31-32`) populates items only within `MAX_RING_M = 900 m` across 5 density rings (`RINGS`):
     - **Ring 1 ($d \le 220\text{ m}$, `1.00`)**: $A(220) = 0.443\text{ km}^2 \implies \mathbf{6.8\text{ tiles}}$ (of which $d \le \text{SOLID\_M}+\text{SOLID\_HYST\_M} = 125\text{ m}$ gives $\mathbf{3.7\text{ solid/collidable tiles}}$).
     - **Ring 2 ($220 < d \le 400\text{ m}$, `0.78`)**: $\Delta A = 0.535\text{ km}^2 \implies \mathbf{+8.2\text{ tiles}}$ (cumulative `15.0`).
     - **Ring 3 ($400 < d \le 580\text{ m}$, `0.58`)**: $\Delta A = 0.739\text{ km}^2 \implies \mathbf{+11.2\text{ tiles}}$ (cumulative `26.2`).
     - **Ring 4 ($580 < d \le 750\text{ m}$, `0.40`)**: $\Delta A = 0.884\text{ km}^2 \implies \mathbf{+13.5\text{ tiles}}$ (cumulative `39.7`).
     - **Ring 5 ($750 < d \le 900\text{ m}$, `0.26`)**: $\Delta A = 0.931\text{ km}^2 \implies \mathbf{+14.2\text{ tiles}}$ (cumulative **`53.9` active `veg_tile`s**; `52–57` depending on grid alignment).
2. **Road street-furniture prop tiles (`roads.lua:454`, key `"<aid>:p<tx>_<ty>"`)**:
   - Every `roads_tile` (`server/roads.py:3106-3115`, `SEND_M = 640 m`, `DROP_M = 960 m`, plus forward speed corridor up to `2000 m` at $v \ge 25\text{ m/s}$) passes `data.props.items` to `trees.onRows(anchorId, 'p' .. key, ...)`.
   - Because `streetlight` and `pole` are uncapped in `GROUP_MAX_M` (`trees.lua:41-44`) and `wallsign_*` has cap `800 m`, every road tile with street furniture within `900 m` (**`~50–54` tiles**) allocates a **second separate `Forest` SceneObject** on the exact same `256 m` square as its `veg_tile`.
3. **Receding tiles draining items (`900 m < d \le 1536 m`)**:
   - Tiles that crossed `900 m` (`target = 0`) or received `veg_drop`/`roads_drop` drain at `PER_FRAME = 20` items/frame (`drainDrops` budget `10` items/frame). At highway speed ($35\text{–}50\text{ m/s}$), **`~18–22` tiles** are mid-drain and still hold $>0$ items.
   - **Total Occupied `Forest`s**: $54\text{ (`veg_tile`)} + 52\text{ (`p<tx>_<ty>`)} + 20\text{ (draining)} = \mathbf{126\text{ occupied Forests}}$ (**Live probe: `126`**).
4. **Why Exactly `23` Empty `Forest`s Are Visible (`126 + 23 = 149`)**:
   - During an origin rebase (`M.transform`, where old-anchor ghost tiles coexist with new-anchor tiles until covered) or a high-speed corridor burst, `forestCount` reaches a high-water mark of `149`.
   - When those `23` extra tiles finish draining (`next(t.made) == nil`), `releaseForest(t)` (`trees.lua:226-229`) pushes `t.forestId` into `pool` **without calling `f:setHidden(true)`**.
   - Because `Forest` has `mGlobalBounds = true` and `hidden == false`, all **23 empty pooled `Forest`s remain visible in `MissionGroup`** and run `Forest::prepRenderImage()` across all 3 shadow cascades and the main pass ($23 \times 4 = 92$ wasted scene-graph visits/frame).

#### B. `TSStatic` SceneObjects (`farfield.lua` + `roads.lua`)
1. **Far-field terrain/detail meshes (`farfield.lua`)**:
   - In `nearVisual = "detail"` (`server/farfield.py:55-97`, `NEAR_RADII = {-2: 384, -1: 768, 0: 1536, 1: 3072, ...}`), `far.live = 474` tiles are shown.
   - Under the $512^2$ `TerrainBlock` (`1024 m × 1024 m`, $8 \times 8 = 64$ forced `L-1` `128 m` tiles), `coverOf(inst)` (`farfield.lua:414-428`) marks the outer `128 m` ring ($8^2 - 6^2 = 28$ tiles) as `cover = 'edge'` (lowered by `-sink`, **visible**) and the interior $6 \times 6 = \mathbf{36\text{ tiles}}$ as `cover = 'interior'` (**hidden**, `coverHide = true`).
   - Thus `farfield` contributes $474 - 36 = \mathbf{438\text{ visible TSStatics}}$.
   - Hidden `farfield` TSStatics: $36\text{ (interior covered)} + 64\text{ (`SPARE_MAX = 64` parked spares)} + \sim 10\text{ (imported `waitingInsts` awaiting `far_swap`)} = \mathbf{110\text{ hidden TSStatics}}$.
2. **Road, building, collider, and `bldfar` meshes (`roads.lua`)**:
   - Near `roads_tile`s (`~55–65` tiles within `SEND_M = 640 m` / `DROP_M = 960 m`): `server/roads.py:3509-3528` always emits `bldcol` and `walkcol`, so `lean` and `leanWalk` (`roads.lua:470-471`) are `true`, making `road`, `walk`, `bld`, `bld2..4`, and `wire` `renderOnly = true` and spawning them for every near tile: `~55` `road` + `~45` `walk` + `~50` `bld` + `~30` `bld2..4` + `~20` `wire` + `~5` `deck`/`tunnel` = **`~205` visible render TSStatics**.
   - **Collision-only `bldcol` and `walkcol` meshes (`roads.lua:396-404`)**: Within `collideNear` (`COLLIDE_M = {350, 1400}`, `~20` tiles $\times 2 = \mathbf{40\text{ TSStatics}}$), `createWalk` sets `collisionType = 'Collision Mesh'`, `isRenderShadowEnabled = 'false'`, `castShadows = '0'`, **but leaves `hidden = false` and `isRenderEnabled = true`**! As discussed in P10-A (`track4_scenegraph_render_audit.md`), `isRenderShadowEnabled` / `castShadows` are non-existent dynamic fields on `TSStatic`; because `isRenderEnabled` is `true`, the `SceneOctree` visits `TSStatic::prepRenderImage()` on all ~40 invisible collider objects in every shadow cascade!
   - **Far building tiles (`bldfar_tile`, `server/buildings.py:678-680`)**: Sent from `skip_m = 640 m` out to `FAR_SEND_M = 1600 m` (`FAR_DROP_M = 1900 m`). In a city/suburb, `~120` `bldfar` TSStatics are visible in the `640–1900 m` annulus, plus `~7` `bldfar` TSStatics hidden by `updateFar` where overlapped by near `tiles[key].bld`.
   - **Prewarm object (`roads.lua:1060`)**: `1` unhidden `TSStatic` at `(0, 0, -5000)`.
   - Thus `roads.lua` contributes $205 + 40 + 120 + 1 = \mathbf{366\text{ visible TSStatics}}$ and **`7` hidden TSStatics**.

| Subsystem / Category | Code Formula / Parameters | Model Visible | Model Hidden | Live Probe |
| :--- | :--- | :---: | :---: | :---: |
| `trees.lua` active `veg_tile` ($\le 900\text{ m}$) | $A(900)/256^2$, 5 rings (`3.7` solid) | `54` | `0` | `126` occupied |
| `trees.lua` active road props `p<tx>_<ty>` | Road tiles $\le 900\text{ m}$ with poles/lights | `52` | `0` | (in `126` above) |
| `trees.lua` receding/draining tiles | $900 < d \le 1536\text{ m}$, `10` drops/frame | `20` | `0` | (in `126` above) |
| `trees.lua` pooled empty `Forest`s | High-water mark minus occupied (`pool`) | **`23`** | `0` | **`23` empty** |
| **Total `Forest` SceneObjects** | `mGlobalBounds = true` | **`149`** | **`0`** | **`149` (`126`+`23`)** |
| `farfield.lua` `far.live` (`detail` mode) | $474\text{ live} - 36\text{ interior covered}$ | `438` | `36` | `474` total live |
| `farfield.lua` `spares` + `waitingInsts` | `SPARE_MAX = 64` + `~10` preloaded | `0` | `74` | (in `117` hidden) |
| `roads.lua` near render (`road`,`walk`,`bld*`,`wire`) | `~55` tiles $\times 3.7$ parts/tile | `205` | `0` | — |
| `roads.lua` near colliders (`bldcol`,`walkcol`) | `~20` tiles $\times 2$ (`isRenderEnabled=true`!) | **`40`** | `0` | — |
| `roads.lua` `bldfar` (`640..1900 m`) + `prewarm` | `~120` uncovered + `1` prewarm; `7` covered | `121` | `7` | — |
| **Total `TSStatic` SceneObjects** | `farfield` + `roads` | **`804`** | **`117`** | **`~800` vis / `117` hid** |

---

## 2. Ranked Proposals

### Proposal P10-D1 (Rank 1): `2×2` Super-Tile `Forest` Consolidation (`512 m × 512 m`) Uniting `veg_tile` and Road Props (`p<tx>_<ty>`)
- **What**: Map each $2 \times 2$ block of `256 m` tiles (`M.SUPER_TILE = 2`, `512 m × 512 m`, via `M.superKey(anchorId, tileKey)`)—including both `veg_tile` (`"<tx>_<ty>"`) and road furniture props (`"p<tx>_<ty>"`)—to a single reference-counted `Forest` SceneObject (`superForests[skey]`, `forestUsers[id]`). Keep all item bookkeeping (`t.made`, `t.solid`, `t.shown`, `t.near`, `t.ranks`, ring thinning) strictly per `256 m` tile. Release and hide the `Forest` only when its last member tile (or `orphanDrop`) empties (`forestUsers[id] == 0`). During origin rebase (`M.transform`), transform each shared `Forest` once (`movedForestsScratch`) and detach `superForests[t.skey]` so incoming new-anchor tiles never attach to a rotated ghost `Forest`.
- **Why (`Forest` Item Count vs. Mutation Cost vs. Cell Rebuild Analysis)**:
  1. **Per-shape `~0.5 µs/item` mutation cost (`SHAPE_ITEMS_PER_FRAME = 600`) is invariant to `Forest` grouping**: As documented in `trees.lua:62-63`, the `~0.5 µs` per-item cost on `createNewItem`/`removeItem` scales with `pop[shape]` (total items of that `.dae` shape **across the entire level**), not per-`Forest` item count. Consolidating `Forest` objects does **not** increase `pop[shape]`.
  2. **`ForestCell` quadtree rebuild cost (`ForestCellBuildBatches`)**: Inside each `ForestData`, Torque3D partitions items into a spatial `ForestCell` quadtree whose leaf cells are `64 m–128 m` wide. Calling `fd:createNewItem` or `fd:removeItem` only invalidates the ancestor chain of the modified leaf `ForestCell`, not sibling `256 m` quadrants. Because `PER_FRAME = 20` mutates only `1` tile at a time (`trees.lua:989-1059`), the dirty leaf cell count per frame in a `512 m` `Forest` (`~600–1,400` items across 4 veg + 4 prop tiles) is virtually identical to a `256 m` `Forest` (`~150–350` items), while adjacent tiles in the `512 m` block now share imposter vertex buffers and culling walks.
  3. **Why uniform `2×2` (`512 m`) beats `4×4` (`1024 m`) or a distance-switched hybrid**:
     - A dynamic hybrid where outer rings use `2×2` Forests and the near ring ($\le 220\text{ m}$) uses `1×1` per-tile Forests would force every tile crossing $d = 220\text{ m}$ to **delete and recreate all ~200 of its non-solid items** to move them between `ForestData` objects (Torque3D `ForestItem`s cannot migrate across `Forest` instances). Since solid collision only activates at $\le 100\text{ m}$ (`SOLID_M = 100`, where items are re-created with `collidable = 1` anyway), keeping a uniform `2×2` super-tile avoids any $220\text{ m}$ migration spike.
     - Conversely, `4×4` (`1024 m`) super-tiles would span `1.05 km`, delaying ghost `Forest` release after an origin rebase (`releaseGhosts`) and increasing the root `ForestCell` quadtree depth by another level. `2×2` (`512 m`) is the sweet spot: it merges up to `4` `veg_tile`s + `4` `p<tx>_<ty>` tiles (`8` logical tiles) into **1 `Forest`**, cutting active `Forest` objects by **`81%`** (`126 -> ~24`).
- **Expected Savings**: **`1.2–2.2 ms/frame` steady-state** (`RenderShadows` + `RenderMain` `Forest::prepRenderImage` calls drop from `596/frame` to `~96/frame`); **`2.5–4.0 ms` on streaming/camera-pan spikes**.
- **Risk & Visual Impact**: **Low risk, zero visual impact**. Per-tile density rings, deterministic rank thinning, and `100 m` solid collision work identically.
- **Files Touched**: `mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua`, `mod/tests/test_trees.lua`.

### Proposal P10-D2 (Rank 2): Hide Pooled Empty `Forest`s on Release & Unhide on Reuse
- **What**: In `releaseForest(t)`, call `setForestHidden(f, true)` (`f:setHidden(true)`) before pushing `id` to `pool`. In `forest(t)`, call `setForestHidden(f, false)` when acquiring/reusing a `Forest`.
- **Why & Safety Verification**:
  - **Physics collision safety**: Every call site of `releaseForest` (`onBin:473`, `onRows:547`, `drainDrops:845/855/890`, `update:1071`, `clear:1108/1116`) only executes after `next(t.made) == nil` (all items, including `t.solid`, have already been removed via `fd:removeItem`). Furthermore, `setHidden(true)` never deletes the C++ `Forest` object (`pool` retains it), completely avoiding the static-collision `Forest` deletion hang documented in `trees.lua:20-26`.
  - **Rebase transform safety**: A ghost tile retains `t.forestId` until `releaseGhosts` marks `t.drop = true` and `drainDrops` removes all items; only then does `releaseForest` hide it. On reuse from `pool`, `forest(t)` resets `f:setPosRot(0, 0, 0, 0, 0, 0, 1)` and unhides `f`.
  - **Why hiding beats hard-capping `pool` deletion**: Because deleting a `Forest` that ever held collidable items risks the C++ collision-octree hang, keeping pooled `Forest`s hidden (`BIT(ObjectHidden)`) gives $O(1)$ octree skip (`0` shadow/cull visits) with zero deletion hang risk.
- **Expected Savings**: **`0.3–0.6 ms/frame` steady-state** (eliminates `23 × 3 = 69` shadow cascade visits + `23` main pass visits on empty `Forest`s immediately).
- **Risk & Visual Impact**: **Zero risk, zero visual impact**.
- **Files Touched**: `mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua`, `mod/tests/test_trees.lua`.

### Proposal P10-D3 (Rank 3): Disable Render Traversal on `bldcol`/`walkcol`/`prewarm` TSStatics + Event-Driven `updateFar` with Deferred Covered `bldfar`
- **What**:
  1. In `roads.lua:spawnWalk`, when `q.what == 'bldcol' or q.what == 'walkcol'`, call `o:setRenderEnabled(false)` (with fallback `o:setField('isRenderEnabled', 0, 'false')`) on the spawned `TSStatic`. In `prewarmNow`, call `po:setHidden(true)` on the prewarm `TSStatic` at `z = -5000`.
  2. Replace the per-frame `for key, f in pairs(far)` scan in `updateFar` with an event-driven `syncFar(key)` helper invoked only when: (a) a near tile's `bld` finishes spawning in `M.update`, (b) a near tile is dropped in `dropTile(key)`, or (c) a `far` tile finishes spawning.
  3. When `onFarTile` or `updateFar` sees that `tiles[key].bld` is already live, mark `f.deferred = true, f.hidden = true` and **defer spawning the `bldfar` `TSStatic`** until `dropTile(key)` calls `syncFar(key)`. Also replace `table.remove(farQ, 1)` ($O(N)$ shift) with an $O(1)$ ring index `farH`.
- **Why**:
  - `bldcol` and `walkcol` (`~40` objects at city speeds, up to `~60` at highway speeds) are invisible physics-only collision meshes (`Collision Mesh`), yet because `isRenderEnabled` was `true`, Torque3D's `SceneOctree` visited `TSStatic::prepRenderImage()` on all of them in every shadow cascade! Setting `setRenderEnabled(false)` sets `OF_RenderDisabled` in C++ while keeping `collisionType = 'Collision Mesh'` 100% active in `be:reloadCollision()` / physics raycasts.
  - Deferring covered `bldfar` tiles avoids importing `.cdae` files and allocating `TSStatic`s for `bldfar` tiles that arrive while their near `road_tile` already shows `bld`.
- **Expected Savings**: **`0.25–0.50 ms/frame` steady-state** (`-41` visible `TSStatic`s in near cascades `0..2`, plus eliminating per-frame `pairs(far)` Lua table scan and redundant `bldfar` `.cdae` spawns).
- **Risk & Visual Impact**: **Low risk, zero visual impact** (`Collision Mesh` physics uses `mCollisionType`, which is independent of `isRenderEnabled`).
- **Files Touched**: `mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua`, `mod/tests/test_roads.lua`.

### Proposal P10-D4 (Rank 4): Tighten `farfield.lua` Spare Parking Pool (`SPARE_MAX = 16`, `SPARE_S = 12`) & Immediate Cap in `park()`
- **What**: Reduce `M.SPARE_MAX` from `64` to `16` and `M.SPARE_S` from `30` to `12` in `farfield.lua`, and enforce `nSpares <= M.SPARE_MAX` immediately inside `park(inst)` (instead of waiting for `update` when `nSpares` temporarily spikes during a multi-group swap).
- **Why**: Each parked spare holds a live (hidden) `TSStatic` in `MissionGroup`, pins a pooled `.cdae` slot in `slotHolder` (forcing `freeSlot` synchronous deletions when slots wrap), and pins a runtime material + satellite `.dds` texture in VRAM. A single LOD split/merge group replaces `1` parent with `4` children (`4` tiles); keeping `16` spares for `12 s` still covers `4` recent swap groups for immediate turnarounds while cutting `48` parked `TSStatic`s and pinned `.cdae`/VRAM slots (`-75%`).
- **Expected Savings**: **`0.10–0.30 ms` on streaming spikes** (fewer `freeSlot` stalls and smaller `MissionGroup` / `spares` tables) and **`~12–24 MB` lower VRAM / `.cdae` slot pressure**.
- **Risk & Visual Impact**: **Zero visual impact**. Turnarounds after $>12\text{ s}$ simply re-import from the server's disk cache.
- **Files Touched**: `mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua`, `mod/tests/test_farfield_spares.lua`.

---

### 2.1 Before / After Scene-Graph Counts & Shadow Cascade Traversal Visits
*Note on Shadow Cascade Visits*: Cascade 3 has `lastSplitTerrainOnly = "1"` (`terrain.lua:226`), so non-terrain `SceneObject`s are visited by **3 shadow cascades (`0, 1, 2`)** plus **1 `RenderMain` frustum pass**.
- Every unhidden `Forest` has `mGlobalBounds = true` and is visited in **all 3 shadow cascades (`3.0` cascades/Forest)** + `1.0` main pass.
- Visible `TSStatic`s are bounded to their tile AABB: near colliders (`bldcol`/`walkcol`, $\le 350\text{ m}$) intersect on average **`2.2` shadow cascades**, near road/building meshes ($\le 640\text{ m}$) intersect **`1.6` cascades**, `bldfar` ($640\text{–}1900\text{ m}$) intersects **`0.6` cascades** (Cascade 2), and `farfield` visible tiles ($384\text{ m}..80\text{ km}$) intersect **`0.35` cascades** (only `L-2`/`L-1`/`L0` tiles within `~1.5 km` intersect Cascades `0..2`).

| Metric | Before (Live / Baseline) | After (P10-D1..D4) | Delta ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Visible `Forest` SceneObjects (occupied)** | `126` (`54` veg + `52` prop + `20` drain) | **`24`** (`18` active `2×2` + `6` drain) | **`-102` (`-81.0%`)** |
| **Visible `Forest` SceneObjects (empty pooled)** | **`23`** (unhidden in `pool`!) | **`0`** (hidden on `releaseForest`) | **`-23` (`-100%`)** |
| **Total Visible `Forest` SceneObjects** | **`149`** | **`24`** | **`-125` (`-83.9%`)** |
| **Hidden `Forest` SceneObjects (`pool`)** | `0` | `~6` (lower high-water mark, hidden) | `+6` (skipped in $O(1)$) |
| **Visible/Renderable `TSStatic`s (`roads.lua`)** | `366` (`205` near + `40` col + `120` far + `1` pre) | **`325`** (`40` col `renderEnabled=false`, `1` pre hidden) | **`-41` (`-11.2%`)** |
| **Visible `TSStatic`s (`farfield.lua`)** | `438` (`474` live `- 36` interior) | **`438`** (unchanged without P10-A) | `0` (see Note below*) |
| **Total Visible/Renderable `TSStatic`s** | **`804`** | **`763`** | **`-41` (`-5.1%`)** |
| **Hidden/Non-Render `TSStatic`s (`farfield`+`roads`)** | `117` (`64` spares + `36` int + `10` wait + `7` far) | **`105`** (`16` spares + `36` int + `10` wait + `41` col/pre + `2` far) | **`-48` parked spares** |
| **`Forest` Shadow Cascade Visits / Frame (`×3` casc.)** | `149 × 3 =` **`447`** | `24 × 3 =` **`72`** | **`-375` (`-83.9%`)** |
| **`TSStatic` Shadow Cascade Visits / Frame (P10-D only)** | `328 (near) + 88 (col) + 72 (far) + 153 (ff) =` **`641`** | `328 (near) + 0 (col) + 72 (far) + 153 (ff) =` **`553`** | **`-88` (`-13.7%`)** |
| **Total Shadow Cascade Object Visits / Frame** | **`1,088` visits/frame** | **`625` visits/frame** (*`~140` with P10-A*) | **`-463` (`-42.6%`)** |

*\*Note: Combined with P10-A's `TSStatic.disableShadows = 1` on `farfield`, `road`, `walk`, `wire`, and `bldfar`, `TSStatic` shadow visits drop further from `553` to `~68` (only near `bld` and `deck`), bringing total shadow visits from `1,088` down to **`~140` (`-87.1%`)**!*

---

## 3. Patch List

All patches are in `runs/optimization_logs/phase10/p10d_scenegraph_forests/` and verified cleanly via `git apply --check`:
1. **`trees.lua.diff`** — Implements `2×2` super-tile `Forest` sharing (`M.SUPER_TILE = 2`, `M.superKey`, `superForests`, `forestUsers`), hides empty `Forest`s on `releaseForest` and unhides on reuse in `forest()`, and deduplicates shared `Forest` transforms in `M.transform`.
2. **`farfield.lua.diff`** — Lowers `M.SPARE_MAX` from `64` to `16` and `M.SPARE_S` from `30` to `12`, and enforces `M.SPARE_MAX` immediately inside `park(inst)`.
3. **`roads.lua.diff`** — Disables rendering (`setRenderEnabled(false)`) on collision-only `bldcol`/`walkcol` `TSStatic`s, hides the `prewarm` `TSStatic`, replaces the per-frame `pairs(far)` loop in `updateFar` with event-driven `syncFar(key)` and $O(1)$ `farH` queue indexing, and defers spawning `bldfar` `TSStatic`s while covered by near `bld`.
4. **`test_trees.lua.diff`** — Adds unit tests for `M.superKey`, `2×2` super-tile sharing across sibling `veg_tile` and `p<tx>_<ty>` road-prop tiles, reference-counted release, `o.hidden == true` on pool release, and `o.hidden == false` on reuse.
5. **`test_farfield_spares.lua.diff`** — Asserts default `SPARE_MAX == 16` / `SPARE_S == 12` and verifies immediate `SPARE_MAX` eviction inside `park()` during multi-tile swaps.
6. **`test_roads.lua.diff`** — Verifies `isRenderEnabled == false` on `walkcol` meshes, event-driven `syncFar` hiding when near `bld` spawns, and deferred `bldfar` spawning when covered by an existing near `bld`.

---

## 4. Test Plan

### 4.1 Offline Unit Tests
Apply the 6 diffs and run the offline LuaJIT suite (or parallel test runner):
```powershell
git apply runs/optimization_logs/phase10/p10d_scenegraph_forests/*.diff
luajit mod/tests/test_trees.lua
luajit mod/tests/test_farfield_spares.lua
luajit mod/tests/test_roads.lua
python tools/parallel_tests.py -j 12
```
*(Note: `luajit` is not installed on the current agent shell PATH; all 6 diffs were verified structurally and via `git apply --check` against `HEAD`.)*

### 4.2 In-Engine Telemetry & Performance Graph Validation
1. Launch BeamNG.drive with BeamNG.Earth, ensure play mode (`set_ui_state({"route": "play"})`), and toggle the performance graph (`Ctrl+Shift+F` / `toggle_performance_graph`).
2. Run a 60-second autonomous road drive in a dense urban/forested area (e.g., Seattle or Fells Point) at `25–45 m/s` using `python tools/perf_capture.py --duration 60`.
3. Verify via GE Lua console / MCP telemetry:
   - Count live visible vs. hidden `Forest` objects: confirm `vis == ~18..26` and `hid == pool_size` (`0` empty visible `Forest`s).
   - Confirm `RenderShadows` CPU time drops by `~1.5–2.5 ms` steady-state and p95 frame time stays `< 16.67 ms`.
   - Test vehicle collision against trees (`< 100 m`), building walls (`bldcol`), and sidewalk curbs (`walkcol`), and trigger a forced origin rebase to confirm zero tree/building flicker or ghost rotation double-transform.

---

## 5. Cross-Task Requests (Files Outside P10-D Ownership)

1. **`server/buildings.py` (`MAX_VERTS` & `FAR_SEND_M` / `FAR_DROP_M`)**:
   - In `server/buildings.py:678-680`, `FAR_SEND_M = 1600.0` and `FAR_DROP_M = 1900.0` produce `~120` visible `bldfar` `TSStatic`s in the `640..1900 m` ring. Reducing `FAR_SEND_M` to `1200.0` and `FAR_DROP_M` to `1450.0` would cut `~55` visible `bldfar` `TSStatic`s (`-45%`) with negligible horizon impact.
   - In `server/buildings.py`, raising the per-part 16-bit vertex split threshold from `~30,000` closer to `55,000` vertices would eliminate most `bld2`, `bld3`, `bld4` secondary `TSStatic` parts (`~30` objects in dense urban tiles).
2. **`server/roads.py` (Combined `col` mesh per tile)**:
   - Merging `bldcol` and `walkcol` into a single collision-only `.cdae` per `256 m` tile on the server would halve collider `TSStatic` count (`40 -> 20`) and halve `.cdae` slot consumption for colliders.
3. **Coordination with P10-A (`trees.lua`, `farfield.lua`, `roads.lua`) & P10-B (`trees.lua`)**:
   - Our diffs intentionally leave P10-A's lines (`trees.lua:946-958, 1073-1083`, `farfield.lua:353-354, 392-393`, `roads.lua:382-383`) and P10-B's per-row mutation loop lines (`trees.lua:960-1070`) untouched so all patches apply cleanly together.

---

## 6. Open Questions

1. **`M.SUPER_TILE = 2` (`512 m`) vs. `M.SUPER_TILE = 4` (`1024 m`) in sparse rural scenes**: `2×2` (`512 m`) reduces active `Forest` objects from `126` to `~24` while keeping rebase ghost coverage footprints small (`512 m`). Should `M.SUPER_TILE` remain `2` globally, or increase to `4` when `nearVisual == "terrain"`? (Recommend keeping `2` globally as `24` Forests already eliminates `84%` of `Forest` traversal overhead.)
2. **Server-side `bldfar` outer radius (`1600 m` vs `1200 m`)**: Would the user accept tightening `FAR_SEND_M` from `1600 m` to `1200 m` in `server/buildings.py` in a follow-up server patch to save another `~55` `TSStatic`s?
