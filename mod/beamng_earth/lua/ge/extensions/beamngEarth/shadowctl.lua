-- Opt-in BeamNG 0.40 Shadow Control Surface & Burst-Gated Shadow Profile (RFC #3 PoC).
--
-- Disabled by default (`M.enabled == false`, driven by settings.lua `shadowControl = false`).
-- When disabled, this module performs zero engine mutations (no sunsky.texSize changes, no
-- PSSMLightShadowMap writes, no object modifications) and zero global GC overrides.
-- When opted in:
--   - `M.apply(targetSun)` caps sun shadow texSize at `SUN_TEX_SIZE` (never raising a smaller
--     default such as 512) and applies shadow distance / logWeight / split settings, cleanly
--     restorable via `M.restore()`.
--   - `M.applyGlobalProfile(speedMps, gov, dtReal)` applies velocity-adaptive shadow distance
--     scaling (0.45 -> 0.25 between 20 and 60 m/s) and burst-gated tightening (default 0.22)
--     on structural streaming bursts, with throttled C++ userdata writes (`UPDATE_INTERVAL_S`
--     and `SCALE_EPS` deadband).

local M = {}

M.enabled = false

M.BASE_SCALE = 0.45
M.FAST_SCALE = 0.25
M.SPEED_LO_MPS = 20.0
M.SPEED_SPAN_MPS = 40.0
M.BURST_ENABLED = true
M.BURST_SCALE = 0.22
M.BURST_SCALE_MIN = 0.10
M.BURST_SCALE_MAX = 0.45
M.BURST_HOLD_S = 1.05
M.BURST_RELEASE_S = 0.60
M.BURST_RAMP_S = M.BURST_RELEASE_S
M.SCALE_EPS = 0.005
M.UPDATE_INTERVAL_S = 0.05
M.FORCE_ENGINE_MODE = false

M.SUN_TEX_SIZE = 1024
M.SUN_SHADOW_DISTANCE = 600
M.SUN_LOG_WEIGHT = 0.90
M.SUN_LAST_SPLIT_TERRAIN_ONLY = true
M.SUN_OVER_DARK_FACTOR = '2000 1000 500 200'

-- Module-level diagnostics table updated in place (zero per-frame allocation).
M.state = {
  scale = M.BASE_SCALE,
  burstBlend = 0.0,
  holdS = 0.0,
  triggers = 0,
  writes = 0,
}

local caps = nil
local lastScale = nil
local lastSplitDisabled = nil
local burstHold = 0.0
local burstBlend = 0.0
local burstPending = false
local updateAcc = M.UPDATE_INTERVAL_S
local origSunFields = nil
local origPssmFields = nil

local min, max, abs = math.min, math.max, math.abs

function M.isEnabled()
  return M.enabled == true
end

function M.setEnabled(on)
  local want = (on == true)
  if M.enabled == want then return M.enabled end
  M.enabled = want
  if not want then
    M.restore()
  else
    updateAcc = M.UPDATE_INTERVAL_S
  end
  return M.enabled
end

-- Feature-detect verified engine shadow controls once (pcall-guarded, cached).
function M.probe()
  if caps then return caps end
  local c = {
    pssm = false,
    renderSettings = false,
    shadowMapPass = false,
    imposterCanShadow = false,
  }
  local pssm = rawget(_G, 'PSSMLightShadowMap')
  if type(pssm) == 'table' or type(pssm) == 'userdata' then
    local ok, v = pcall(function() return pssm.sdsmMaxDistanceScale end)
    c.pssm = ok and type(v) == 'number'
  end
  local rs = rawget(_G, 'RenderSettings')
  if type(rs) == 'table' and type(rs.getGlobals) == 'function' then
    local ok, rg = pcall(rs.getGlobals)
    c.renderSettings = ok and rg ~= nil
  end
  local smp = rawget(_G, 'ShadowMapPass')
  if type(smp) == 'table' or type(smp) == 'userdata' then
    local ok, v = pcall(function() return smp.disableShadows end)
    c.shadowMapPass = ok and type(v) == 'boolean'
  end
  local getCvar = rawget(_G, 'getConsoleVariable')
  if type(getCvar) == 'function' then
    local ok, v = pcall(getCvar, string.char(36) .. 'pref::imposter::canShadow')
    c.imposterCanShadow = ok and v ~= nil and v ~= ''
  end
  caps = c
  return caps
end

-- Signal that a Forest/scene-structure mutation occurred so onPreRender can tighten the shadow
-- cascade when opted in. O(1), no scans.
function M.noteBurst()
  if not M.enabled then return end
  burstPending = true
end

M.onForestTileUpdated = M.noteBurst

-- Exclude or cheapen a scene object in the shadow pass when opted in.
function M.excludeObject(obj, kind)
  if not M.enabled or not obj then return false end
  local isStubTable = (type(obj) == 'table' and type(obj.fields) == 'table' and not M.FORCE_ENGINE_MODE)

  if kind == 'far' or kind == 'road_static' or kind == 'bldfar' or kind == 'walk' or kind == 'road' then
    if isStubTable then
      obj.fields.isRenderShadowEnabled = 'false'
      obj.fields.castShadows = '0'
    end
    return true
  end

  if kind == 'forest_empty' then
    pcall(function()
      if obj.setHidden then obj:setHidden(true) else obj.hidden = true end
      if obj.setField then obj:setField('isRenderEnabled', 0, 'false') end
    end)
    return true
  end

  return false
end

-- Pure helper: target sdsmMaxDistanceScale for a given speed (m/s) and burst blend [0..1].
function M.computeDistanceScale(speedMps, blend)
  local spd = max(0.0, tonumber(speedMps) or 0.0)
  local t = min(1.0, max(0.0, (spd - M.SPEED_LO_MPS) / M.SPEED_SPAN_MPS))
  local scale = M.BASE_SCALE - (M.BASE_SCALE - M.FAST_SCALE) * t
  local b = min(1.0, max(0.0, tonumber(blend) or 0.0))
  if b > 0.0 then
    local burstScale = min(M.BURST_SCALE_MAX, max(M.BURST_SCALE_MIN, tonumber(M.BURST_SCALE) or 0.22))
    local targetBurst = min(scale, burstScale)
    scale = scale - (scale - targetBurst) * b
  end
  return scale
end

-- Called from core.lua `onPreRender(dtReal, dtSim)` only when opted in (`M.enabled == true`).
function M.applyGlobalProfile(speedMps, gov, dtReal)
  if not M.enabled then return nil end
  local dt = max(0.0, tonumber(dtReal) or (1.0 / 60.0))

  local pending = burstPending
  burstPending = false

  local loading = gov ~= nil and gov.loading == true
  local structTrig = pending or (gov ~= nil and (((gov.sceneStructCount or 0) > 0) or (gov.burst == true)))

  if loading or not M.BURST_ENABLED then
    burstHold = 0.0
    burstBlend = 0.0
  elseif structTrig then
    burstHold = M.BURST_HOLD_S
    burstBlend = 1.0
    M.state.triggers = M.state.triggers + 1
  elseif burstHold > 0.0 then
    if dt <= burstHold then
      burstHold = burstHold - dt
      burstBlend = 1.0
    else
      local rem = dt - burstHold
      burstHold = 0.0
      local rel = M.BURST_RELEASE_S
      burstBlend = (rel and rel > 0.0) and max(0.0, 1.0 - rem / rel) or 0.0
    end
  elseif burstBlend > 0.0 then
    local rel = M.BURST_RELEASE_S
    if rel and rel > 0.0 then
      burstBlend = max(0.0, burstBlend - dt / rel)
    else
      burstBlend = 0.0
    end
  end

  local scale = M.computeDistanceScale(speedMps, burstBlend)
  M.state.scale = scale
  M.state.burstBlend = burstBlend
  M.state.holdS = burstHold

  local pssm = rawget(_G, 'PSSMLightShadowMap')
  if not pssm then return nil end

  updateAcc = updateAcc + dt
  local immediate = structTrig or lastScale == nil
  if not immediate and updateAcc < M.UPDATE_INTERVAL_S then
    return scale
  end
  updateAcc = 0.0

  if not origPssmFields then
    local okS, origS = pcall(function() return pssm.sdsmMaxDistanceScale end)
    local okL, origL = pcall(function() return pssm.lastSplitCastersEnabled end)
    origPssmFields = {
      sdsmMaxDistanceScale = okS and origS or nil,
      lastSplitCastersEnabled = okL and origL or nil,
    }
  end

  if lastSplitDisabled ~= true then
    pcall(function()
      if pssm.lastSplitCastersEnabled ~= false then
        pssm.lastSplitCastersEnabled = false
        M.state.writes = M.state.writes + 1
      end
      lastSplitDisabled = true
    end)
  end

  if not lastScale or abs(scale - lastScale) >= M.SCALE_EPS
      or abs((pssm.sdsmMaxDistanceScale or 0) - scale) >= M.SCALE_EPS then
    pssm.sdsmMaxDistanceScale = scale
    lastScale = scale
    M.state.writes = M.state.writes + 1
  end
  return scale
end

local function findSun()
  local sun = nil
  local st = rawget(_G, 'scenetree')
  if st and st.findObject then
    sun = st.findObject('sunsky') or st.findObject('Sun')
  end
  if not sun and st and st.findClassObjects then
    local list = st.findClassObjects('ScatterSky')
    if list and list[1] and st.findObject then
      sun = st.findObject(list[1])
    end
    if not sun then
      list = st.findClassObjects('Sun')
      if list and list[1] and st.findObject then
        sun = st.findObject(list[1])
      end
    end
  end
  if not sun then
    local gSun = rawget(_G, 'Sun')
    if type(gSun) == 'table' or type(gSun) == 'userdata' then sun = gSun end
  end
  return sun
end

local function readSunField(obj, k)
  if not obj then return nil end
  if obj.getField then
    local ok, v = pcall(obj.getField, obj, k)
    if ok and v ~= nil then return v end
  end
  local ok, v = pcall(function() return obj[k] end)
  if ok and v ~= nil then return v end
  return nil
end

local function writeSunField(obj, k, v)
  if not obj then return end
  pcall(function()
    if obj.setField then
      if v ~= nil then
        obj:setField(k, 0, tostring(v))
      else
        obj:setField(k, 0, nil)
      end
    end
  end)
  pcall(function()
    obj[k] = v
  end)
end

function M.apply(targetSun)
  if not M.enabled then return false end
  local sun = targetSun or findSun()
  if not sun then return false end

  if not origSunFields then
    origSunFields = {
      sun = sun,
      texSize = readSunField(sun, 'texSize'),
      shadowDistance = readSunField(sun, 'shadowDistance'),
      logWeight = readSunField(sun, 'logWeight'),
      lastSplitTerrainOnly = readSunField(sun, 'lastSplitTerrainOnly'),
      overDarkFactor = readSunField(sun, 'overDarkFactor'),
    }
  end

  local origTex = tonumber(origSunFields and origSunFields.texSize)
  local targetTex = (origTex and origTex > 0 and origTex < M.SUN_TEX_SIZE) and origTex or M.SUN_TEX_SIZE
  writeSunField(sun, 'texSize', targetTex)
  writeSunField(sun, 'shadowDistance', M.SUN_SHADOW_DISTANCE)
  writeSunField(sun, 'logWeight', M.SUN_LOG_WEIGHT)
  writeSunField(sun, 'lastSplitTerrainOnly', M.SUN_LAST_SPLIT_TERRAIN_ONLY)
  writeSunField(sun, 'overDarkFactor', M.SUN_OVER_DARK_FACTOR)
  pcall(function() if sun.postApply then sun:postApply() end end)
  return true
end

function M.restore(targetSun)
  local sun = targetSun or (origSunFields and origSunFields.sun) or findSun()
  if origSunFields and sun then
    writeSunField(sun, 'texSize', origSunFields.texSize)
    writeSunField(sun, 'shadowDistance', origSunFields.shadowDistance)
    writeSunField(sun, 'logWeight', origSunFields.logWeight)
    writeSunField(sun, 'lastSplitTerrainOnly', origSunFields.lastSplitTerrainOnly)
    writeSunField(sun, 'overDarkFactor', origSunFields.overDarkFactor)
    pcall(function() if sun.postApply then sun:postApply() end end)
  end
  origSunFields = nil

  local pssm = rawget(_G, 'PSSMLightShadowMap')
  if origPssmFields and pssm then
    if origPssmFields.sdsmMaxDistanceScale ~= nil then
      pcall(function() pssm.sdsmMaxDistanceScale = origPssmFields.sdsmMaxDistanceScale end)
    end
    if origPssmFields.lastSplitCastersEnabled ~= nil then
      pcall(function() pssm.lastSplitCastersEnabled = origPssmFields.lastSplitCastersEnabled end)
    end
  end
  origPssmFields = nil
  lastScale = nil
  lastSplitDisabled = nil
  burstHold = 0.0
  burstBlend = 0.0
  burstPending = false
  return true
end

function M.reset()
  M.restore()
  M.enabled = false
  caps = nil
  M.BURST_ENABLED = true
  M.BURST_SCALE = 0.22
  updateAcc = M.UPDATE_INTERVAL_S
  M.state.scale = M.BASE_SCALE
  M.state.burstBlend = 0.0
  M.state.holdS = 0.0
  M.state.triggers = 0
  M.state.writes = 0
end

return M
