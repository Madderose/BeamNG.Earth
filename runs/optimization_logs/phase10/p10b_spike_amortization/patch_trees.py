import sys

path = "runs/optimization_logs/phase10/p10b_spike_amortization/copies/trees.lua"
with open(path, "rb") as f:
    raw = f.read()

has_crlf = b"\r\n" in raw
nl = "\r\n" if has_crlf else "\n"
text = raw.decode("utf-8").replace("\r\n", "\n")

# 1. Add MAX_FORESTS_PER_FRAME after MICRO_SHAPE_ITEMS = 600
old1 = """M.SHAPE_ITEMS_PER_FRAME = 600
M.MICRO_SHAPE_ITEMS = 600"""
new1 = """M.SHAPE_ITEMS_PER_FRAME = 600
M.MICRO_SHAPE_ITEMS = 600
-- Cap of distinct Forest SceneObjects mutated per frame in governed mode: each mutated Forest marks its
-- ForestCell quadtree dirty and rebuilds imposter/mesh vertex batches on the next RenderShadows pass.
-- Batching all rows of 1-2 Forests per frame instead of touching 5-15 Forests avoids O(N_forests) batch rebuild spikes.
M.MAX_FORESTS_PER_FRAME = 2"""
assert old1 in text, "old1 not found"
text = text.replace(old1, new1, 1)

# 2. Add touchedForests tracking next to resetTouched() and allow()
old2 = """-- This frame's shapes: may an item of this shape change now? (see SHAPE_ITEMS_PER_FRAME)
local touched, touchedItems, touchedCount = {}, 0, 0
local function resetTouched()
  M.lastShapeItems = touchedItems        -- the previous frame's (diagnostics)
  for k in pairs(touched) do touched[k] = nil end
  touchedItems, touchedCount = 0, 0
end"""
new2 = """-- This frame's shapes and distinct Forests: may an item of this shape/Forest change now?
local touched, touchedItems, touchedCount = {}, 0, 0
local touchedForests, touchedForestCount = {}, 0
local function resetTouched()
  M.lastShapeItems = touchedItems        -- the previous frame's (diagnostics)
  M.lastForestsTouched = touchedForestCount
  for k in pairs(touched) do touched[k] = nil end
  for k in pairs(touchedForests) do touchedForests[k] = nil end
  touchedItems, touchedCount, touchedForestCount = 0, 0, 0
end

local function allowForest(t, maxForests)
  local fk = t.forestId or t
  if touchedForests[fk] then return true end
  if maxForests and touchedForestCount >= maxForests then return false end
  return true
end

local function noteForestTouched(t)
  local fk = t.forestId or t
  if not touchedForests[fk] then
    touchedForests[fk] = true
    touchedForestCount = touchedForestCount + 1
  end
end"""
assert old2 in text, "old2 not found"
text = text.replace(old2, new2, 1)

# 3. Update M.update budgets and drainDrops / orderScratch loops to enforce maxForests and batch per-Forest
old3 = """  local governed = (gov ~= nil)
  local budget, maxRows, maxDemoteRows, maxWallMs
  if governed then
    -- Yield on heavy frames, terrain commit quiet windows, or frames where roads/farfield already ran a unit
    if gov.blocked or gov.heavyPending or (gov.isHeavyFrame and gov:isHeavyFrame())
        or ((gov.frameUnits or 0) > 0) then
      return
    end
    if gov.est and not gov.est[M.GOV_KIND] then
      gov.est[M.GOV_KIND] = M.GOV_PRIOR_MS
    end
    if gov.try and not gov:try(M.GOV_KIND) then
      return
    end
    budget = M.PER_FRAME
    maxRows = M.ROWS_PER_FRAME
    maxDemoteRows = M.MICRO_DEMOTE_ROWS_PER_FRAME
    maxWallMs = M.MAX_WALL_MS
  else
    -- Offline unit test mode (mod/tests/test_trees.lua calls trees.update(aid, player) with gov == nil)
    frameN = frameN + 1
    local n = math.max(1, M.EVERY_N or 1)
    if frameN % n ~= 0 then return end
    budget = math.max(M.PER_FRAME, M.LEGACY_PER_FRAME) * n
    maxRows = math.max(M.ROWS_PER_FRAME, M.LEGACY_ROWS_PER_FRAME)
    maxDemoteRows = 1e9
    maxWallMs = 1e9
  end"""

new3 = """  local governed = (gov ~= nil)
  local budget, maxRows, maxDemoteRows, maxWallMs, maxForests
  if governed then
    -- Yield on heavy frames, terrain commit quiet windows, or frames where roads/farfield already ran a unit
    if gov.blocked or gov.heavyPending or (gov.isHeavyFrame and gov:isHeavyFrame())
        or ((gov.frameUnits or 0) > 0) then
      return
    end
    if gov.est and not gov.est[M.GOV_KIND] then
      gov.est[M.GOV_KIND] = M.GOV_PRIOR_MS
    end
    if gov.try and not gov:try(M.GOV_KIND) then
      return
    end
    budget = M.PER_FRAME
    maxRows = M.ROWS_PER_FRAME
    maxDemoteRows = M.MICRO_DEMOTE_ROWS_PER_FRAME
    maxWallMs = M.MAX_WALL_MS
    maxForests = (gov.burst and 1) or M.MAX_FORESTS_PER_FRAME or 2
  else
    -- Offline unit test mode (mod/tests/test_trees.lua calls trees.update(aid, player) with gov == nil)
    frameN = frameN + 1
    local n = math.max(1, M.EVERY_N or 1)
    if frameN % n ~= 0 then return end
    budget = math.max(M.PER_FRAME, M.LEGACY_PER_FRAME) * n
    maxRows = math.max(M.ROWS_PER_FRAME, M.LEGACY_ROWS_PER_FRAME)
    maxDemoteRows = 1e9
    maxWallMs = 1e9
    maxForests = M.MAX_FORESTS_UNW or nil
  end"""
assert old3 in text, "old3 not found"
text = text.replace(old3, new3, 1)

# 4. In drainDrops, batch all removals of one Forest together and respect allowForest(t, maxForests)
old4 = """      local perTile = governed and math.max(math.ceil(limit / nDrops), 8) or math.max(math.ceil(limit / nDrops), 64)
      local progressed = false
      for idx = 1, nDrops do
        local d = dropsScratch[idx]
        local key, t = d.key, d.t
        local f = t.forestId and scenetree.findObjectById(t.forestId)
        local fd = f and f:getData()
        local tileLimit = perTile
        for i, it in pairs(t.made) do
          if tileLimit <= 0 or limit <= 0 or budget <= 0 or overWallBudget() then
            if overWallBudget() then budget = 0 end
            break
          end
          local sh = t.madeShape[i]
          if not sh or allow(sh) then
            if fd then removeItem(fd, it, sh) end
            t.made[i], t.solid[i], t.madeShape[i] = nil, nil, nil
            tileLimit = tileLimit - 1
            limit = limit - 1
            budget = budget - 1
            progressed = true
          end
        end"""

new4 = """      -- Batch all rows of one dropped Forest together (up to `limit`) instead of slicing across all nDrops Forests
      local perTile = governed and limit or math.max(math.ceil(limit / nDrops), 64)
      local progressed = false
      for idx = 1, nDrops do
        local d = dropsScratch[idx]
        local key, t = d.key, d.t
        if not allowForest(t, maxForests) then
          hasMoreWork = true
        else
          local f = t.forestId and scenetree.findObjectById(t.forestId)
          local fd = f and f:getData()
          local tileLimit = perTile
          for i, it in pairs(t.made) do
            if tileLimit <= 0 or limit <= 0 or budget <= 0 or overWallBudget() then
              if overWallBudget() then budget = 0 end
              break
            end
            local sh = t.madeShape[i]
            if not sh or allow(sh) then
              noteForestTouched(t)
              if fd then removeItem(fd, it, sh) end
              t.made[i], t.solid[i], t.madeShape[i] = nil, nil, nil
              tileLimit = tileLimit - 1
              limit = limit - 1
              budget = budget - 1
              progressed = true
            end
          end"""
assert old4 in text, "old4 not found"
text = text.replace(old4, new4, 1)

old4b = """        if next(t.made) == nil then
          releaseForest(t)
          if not d.isOrphan then
            tiles[key] = nil
          end
        else
          hasMoreWork = true
        end
        if limit <= 0 or budget <= 0 or overWallBudget() then
          hasMoreWork = true
          break
        end
      end"""

new4b = """          if next(t.made) == nil then
            releaseForest(t)
            if not d.isOrphan then
              tiles[key] = nil
            end
          else
            hasMoreWork = true
          end
        end
        if limit <= 0 or budget <= 0 or overWallBudget() then
          hasMoreWork = true
          break
        end
      end"""
assert old4b in text, "old4b not found"
text = text.replace(old4b, new4b, 1)

# 5. Remove no-op isRenderShadowEnabled dynamic field writes in trees.lua and enforce allowForest in main tile loop
old5 = """    local shadowMaxM = (M.RINGS[1] and M.RINGS[1][1]) or 300
    local shadow = dist <= shadowMaxM
    if t.shadow ~= shadow and t.forestId then
      local forestObj = scenetree.findObjectById(t.forestId)
      if forestObj then
        if dist > shadowMaxM then
          forestObj:setField('isRenderShadowEnabled', 0, 'false')
        else
          forestObj:setField('isRenderShadowEnabled', 0, 'true')
        end
      end
      t.shadow = shadow
    end"""

new5 = """    -- Note: Forest has no C++ isRenderShadowEnabled field (shadow culling is handled by TSForestItemData.shadowNullDetailSize)"""
assert old5 in text, "old5 not found"
text = text.replace(old5, new5, 1)

old6 = """      local rowLimit = demote and maxDemoteRows or maxRows
      if rowsScanned > rowLimit or budget <= 0 or overWallBudget() then
        hasMoreWork = true
        break
      end
      local sameTarget = (want == t.shown and band == t.band and near == t.near)
      local wasThinning = want < (t.shown or 0) or (t.band and band < t.band) or (sameTarget and t.thinning)
      local startRow = (sameTarget and t.pending and t.nextRow) or 1
      local nextPending = nil
      t.pending = false
      local fd = nil                          -- the tile's Forest data, made when it first needs an item
      local function data() fd = fd or forest(t):getData(); return fd end"""

new6 = """      local rowLimit = demote and maxDemoteRows or maxRows
      if rowsScanned > rowLimit or budget <= 0 or overWallBudget() then
        hasMoreWork = true
        break
      end
      if not allowForest(t, maxForests) then
        hasMoreWork = true
        goto next_tile
      end
      local sameTarget = (want == t.shown and band == t.band and near == t.near)
      local wasThinning = want < (t.shown or 0) or (t.band and band < t.band) or (sameTarget and t.thinning)
      local startRow = (sameTarget and t.pending and t.nextRow) or 1
      local nextPending = nil
      t.pending = false
      local fd = nil                          -- the tile's Forest data, made when it first needs an item
      local function data()
        if not fd then
          local fObj = forest(t)
          noteForestTouched(t)
          fd = fObj:getData()
        end
        return fd
      end"""
assert old6 in text, "old6 not found"
text = text.replace(old6, new6, 1)

old7 = """      if next(t.made) == nil then
        releaseForest(t)
      elseif t.forestId then
        local forestObj = scenetree.findObjectById(t.forestId)
        if forestObj then
          local shadowMaxM = (M.RINGS[1] and M.RINGS[1][1]) or 300
          if dist > shadowMaxM then
            forestObj:setField('isRenderShadowEnabled', 0, 'false')
            t.shadow = false
          else
            forestObj:setField('isRenderShadowEnabled', 0, 'true')
            t.shadow = true
          end
        end
      end
      t.nextRow = t.pending and nextPending or nil
      t.thinning = (t.pending and wasThinning) or nil
      t.shown = want
      t.band = band
      t.near = near
    end
  end"""

new7 = """      if next(t.made) == nil then
        releaseForest(t)
      end
      t.nextRow = t.pending and nextPending or nil
      t.thinning = (t.pending and wasThinning) or nil
      t.shown = want
      t.band = band
      t.near = near
      ::next_tile::
    end
  end"""
assert old7 in text, "old7 not found"
text = text.replace(old7, new7, 1)

with open(path, "wb") as f:
    f.write(text.replace("\n", nl).encode("utf-8"))
print("Successfully updated copies/trees.lua")
