-- luajit mod/tests/test_shadowctl.lua  (RFC #3 PoC: opt-in shadowctl.lua unit tests)
local dir = (arg and arg[0] or ''):match('^(.*)[/\\]') or '.'
local T = dofile(dir .. '/testlib.lua')
local S = dofile(dir .. '/stubs.lua')

local shadowctl = require('beamngEarth/shadowctl')
local settings = require('beamngEarth/settings')

-- 0. Off by default: zero engine mutations, zero sunsky.texSize changes, zero global GC overrides
T.check(shadowctl.isEnabled() == false, 'shadowctl starts disabled by default')
T.check(settings.defaults().shadowControl == false, 'settings.defaults().shadowControl is false')
for _, p in ipairs(settings.PRESET_ORDER) do
  T.check(settings.PRESETS[p].shadowControl == false, 'preset ' .. p .. ' has shadowControl = false')
end

local pssmWrites = 0
local pssmState = { lastSplitCastersEnabled = true, sdsmMaxDistanceScale = 0.5 }
PSSMLightShadowMap = setmetatable({}, {
  __index = function(_, k) return pssmState[k] end,
  __newindex = function(_, k, v)
    pssmWrites = pssmWrites + 1
    pssmState[k] = v
  end,
})

local stubSun = S.newObject('ScatterSky')
stubSun:registerObject('sunsky')
stubSun:setField('texSize', 0, '2048')
stubSun:setField('shadowDistance', 0, '1600')
stubSun:setField('logWeight', 0, '0.98')
stubSun:setField('lastSplitTerrainOnly', 0, 'false')
stubSun:setField('overDarkFactor', 0, '0 0 0 0')
local postApplies = 0
function stubSun:postApply() postApplies = postApplies + 1 end

T.check(shadowctl.apply() == false, 'apply is a no-op when disabled')
T.check(stubSun:getField('texSize') == '2048' and postApplies == 0, 'sunsky.texSize untouched when disabled')
T.check(shadowctl.applyGlobalProfile(40, { sceneStructCount = 2, burst = true }, 1 / 60) == nil,
  'applyGlobalProfile returns nil when disabled')
T.check(pssmWrites == 0 and pssmState.sdsmMaxDistanceScale == 0.5 and pssmState.lastSplitCastersEnabled == true,
  'PSSMLightShadowMap untouched when disabled')
local stubOff = createObject('TSStatic')
T.check(shadowctl.excludeObject(stubOff, 'far') == false and stubOff:getField('isRenderShadowEnabled') == nil,
  'excludeObject is a no-op when disabled')

-- Verify shadowctl.lua contains no global collectgarbage overrides
do
  local f = io.open(dir .. '/../beamng_earth/lua/ge/extensions/beamngEarth/shadowctl.lua', 'r')
  local src = f and f:read('*a') or ''
  if f then f:close() end
  T.check(src ~= '' and not src:find('collectgarbage', 1, true), 'shadowctl.lua has no collectgarbage calls')
end

-- 1. Pure velocity & streaming-burst distance scale calculation
T.near(shadowctl.computeDistanceScale(0, 0), 0.45, 1e-6, 'stationary, no burst: 0.45')
T.near(shadowctl.computeDistanceScale(20, 0), 0.45, 1e-6, '20 m/s threshold: 0.45')
T.near(shadowctl.computeDistanceScale(40, 0), 0.35, 1e-6, '40 m/s midpoint: 0.35')
T.near(shadowctl.computeDistanceScale(60, 0), 0.25, 1e-6, '60 m/s high speed: 0.25')
T.near(shadowctl.computeDistanceScale(90, 0), 0.25, 1e-6, '90 m/s clamped: 0.25')
T.near(shadowctl.computeDistanceScale(0, 1.0), 0.22, 1e-6, 'stationary + full burst blend: tightened to 0.22')
T.near(shadowctl.computeDistanceScale(0, 0.5), 0.335, 1e-6, 'stationary + half burst blend: interpolated')

-- 2. Opt-in via settings.lua + throttled PSSMLightShadowMap profile
shadowctl.reset()
settings.load()
T.check(settings.set('shadowControl', true).ok and shadowctl.isEnabled() == true,
  'settings.set(shadowControl, true) enables shadowctl')

local stateRef = shadowctl.state
T.check(type(stateRef) == 'table', 'M.state exposed as module-level table')
local caps = shadowctl.probe()
T.check(caps.pssm == true, 'probe detects PSSMLightShadowMap')

local sc1 = shadowctl.applyGlobalProfile(10, { frameUnits = 0, spent = 0, sceneStructCount = 0, burst = false }, 1 / 60)
T.near(sc1, 0.45, 1e-6, 'normal frame applies 0.45 scale when opted in')
T.check(pssmState.lastSplitCastersEnabled == false, 'lastSplitCastersEnabled forced false when opted in')
local writesAfterFirst = pssmWrites
for _ = 1, 10 do
  shadowctl.applyGlobalProfile(10, { frameUnits = 0, spent = 0, sceneStructCount = 0, burst = false }, 1 / 60)
end
T.check(pssmWrites == writesAfterFirst, 'steady speed skips redundant C++ userdata writes')

-- Throttling: gradual speed change between UPDATE_INTERVAL_S ticks defers C++ writes until interval elapses
local writesBeforeRamp = pssmWrites
shadowctl.applyGlobalProfile(35, { frameUnits = 0, spent = 0, sceneStructCount = 0, burst = false }, 0.01)
T.check(pssmWrites == writesBeforeRamp, 'sub-interval update is throttled (no immediate C++ write)')
shadowctl.applyGlobalProfile(35, { frameUnits = 0, spent = 0, sceneStructCount = 0, burst = false }, shadowctl.UPDATE_INTERVAL_S)
T.check(pssmWrites == writesBeforeRamp + 1, 'update writes once throttle interval elapses')

-- 3. No trigger on plain governor units (sceneStructCount == 0, burst == false)
shadowctl.reset()
shadowctl.setEnabled(true)
for _ = 1, 10 do
  local sc = shadowctl.applyGlobalProfile(10, {
    frameUnits = 3,
    spent = 2.8,
    sceneStructCount = 0,
    burst = false,
    loading = false,
  }, 1 / 60)
  T.near(sc, 0.45, 1e-6, 'plain non-structural governor units do not tighten shadow scale')
end
T.check(shadowctl.state.triggers == 0 and shadowctl.state.burstBlend == 0, 'no triggers recorded on plain units')

-- 4. Structural work triggers immediately -> holds >= 1.0 s -> monotonic release >= 0.5 s
shadowctl.reset()
shadowctl.setEnabled(true)
local scTrig = shadowctl.applyGlobalProfile(10, {
  frameUnits = 1,
  sceneStructCount = 1,
  burst = false,
  loading = false,
}, 1 / 60)
T.near(scTrig, 0.22, 1e-6, 'structural trigger reaches burst scale (0.22) immediately')
T.check(shadowctl.state.triggers == 1 and shadowctl.state.burstBlend == 1.0, 'M.state records trigger and burstBlend=1')
T.check(shadowctl.state == stateRef, 'M.state updated in place without table allocation')

local calmGov = { frameUnits = 1, sceneStructCount = 0, burst = false, loading = false }
for i = 1, 60 do
  local scHold = shadowctl.applyGlobalProfile(10, calmGov, 1 / 60)
  T.near(scHold, 0.22, 1e-6, 'hold stays at burst scale through 1.0 s (frame ' .. i .. ')')
end

local prevScale = shadowctl.state.scale
local releaseFrames = 0
local monotonic = true
local inRelease = false
for _ = 1, 120 do
  local scRel = shadowctl.applyGlobalProfile(10, calmGov, 1 / 60)
  if scRel > 0.22 + 1e-6 then inRelease = true end
  if inRelease then
    releaseFrames = releaseFrames + 1
    if scRel + 1e-9 < prevScale then monotonic = false end
    prevScale = scRel
    if scRel >= 0.45 - 1e-6 then break end
  end
end
T.check(monotonic, 'release is monotonic from burst scale back to base scale')
T.check(releaseFrames >= 30, 'release takes >= 0.5 s (>= 30 frames, got ' .. releaseFrames .. ')')
T.near(shadowctl.state.scale, 0.45, 1e-6, 'scale returns to 0.45 after release completes')

-- 5. gov.loading == true prevents tightening
shadowctl.reset()
shadowctl.setEnabled(true)
shadowctl.noteBurst()
local scLoad = shadowctl.applyGlobalProfile(10, {
  sceneStructCount = 4,
  burst = true,
  loading = true,
}, 1 / 60)
T.near(scLoad, 0.45, 1e-6, 'gov.loading=true prevents burst tightening')
T.check(shadowctl.state.burstBlend == 0, 'burstBlend stays 0 while loading')

-- 6. excludeObject works when opted in
local stubFar = createObject('TSStatic')
T.check(shadowctl.excludeObject(stubFar, 'far') == true, 'excludeObject returns true when opted in')
T.check(stubFar:getField('isRenderShadowEnabled') == 'false' and stubFar:getField('castShadows') == '0',
  'excludeObject writes stub fields for offline tests')
local fEmpty = createObject('Forest')
shadowctl.excludeObject(fEmpty, 'forest_empty')
T.check(fEmpty.hidden == true and fEmpty:getField('isRenderEnabled') == 'false', 'forest_empty hides object')

-- 7. Sun / sunsky configuration when opted in (caps 2048 -> 1024, preserves 512 -> 512) & clean opt-out restore
shadowctl.reset()
shadowctl.setEnabled(true)
T.check(shadowctl.apply() == true, 'apply configures sunsky when opted in')
T.check(stubSun:getField('texSize') == '1024', 'sun texSize capped from 2048 to 1024')
T.check(stubSun:getField('shadowDistance') == '600', 'sun shadowDistance set to 600')
T.near(tonumber(stubSun:getField('logWeight')), 0.90, 1e-6, 'sun logWeight set to 0.90')
T.check(stubSun:getField('lastSplitTerrainOnly') == 'true', 'sun lastSplitTerrainOnly set to true')
T.check(stubSun:getField('overDarkFactor') == '2000 1000 500 200', 'sun overDarkFactor set')

-- Toggling shadowControl back off restores both sunsky and PSSMLightShadowMap
settings.set('shadowControl', false)
T.check(shadowctl.isEnabled() == false, 'settings.set(shadowControl, false) disables shadowctl')
T.check(stubSun:getField('texSize') == '2048', 'sun texSize restored to 2048 on opt-out')
T.check(stubSun:getField('shadowDistance') == '1600', 'sun shadowDistance restored on opt-out')
T.near(pssmState.sdsmMaxDistanceScale, 0.5, 1e-6, 'PSSMLightShadowMap.sdsmMaxDistanceScale restored on opt-out')
T.check(pssmState.lastSplitCastersEnabled == true, 'PSSMLightShadowMap.lastSplitCastersEnabled restored on opt-out')

-- Smaller sunsky default (512) is never increased when opted in
local smallSun = S.newObject('ScatterSky')
smallSun:setField('texSize', 0, '512')
shadowctl.setEnabled(true)
T.check(shadowctl.apply(smallSun) == true, 'apply succeeds on 512 sunsky')
T.check(smallSun:getField('texSize') == '512', '512 texSize is preserved (not raised to 1024)')
shadowctl.restore(smallSun)

shadowctl.reset()
T.done('test_shadowctl')
