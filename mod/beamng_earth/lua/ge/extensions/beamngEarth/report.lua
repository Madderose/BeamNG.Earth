-- In-game reports for the user and the friends testing the mod (2026-10-13: "a reporting tool that
-- makes it easy for me to take notes on the world or to record the performance of my game";
-- 2026-10-14: reports become GitHub issues: map issues, performance issues, bugs, ideas).
--
--   Ctrl+Shift+E   a report: the moment is captured at once (screenshot, location, frame times, engine
--                  metrics, the mod's state), then a window takes the kind (Map issue / Performance
--                  issue / Bug / Idea), a short title and the description; Save writes it all.
--   Ctrl+Shift+Y   the performance profiler: 30 s of frame times (and position, every second) while the
--                  player drives; then the same window, kind "Performance issue", with its numbers.
--
-- Reports go to <user folder>/beamngEarth/reports/<date>_<time>_<report|profile>_<n>/ (the game
-- lowercases new folders): report.json, screenshot.jpg, hardware.json (what the engine can tell about
-- the machine and the graphics settings, collectHardware()) and issue.md (a ready-to-post GitHub issue
-- the user edits: issuefmt.lua; tools/reports.py issue N opens it and the new-issue page).
-- reports/index.jsonl gets one line per report. Kinds before 2026-10-14: 'note', 'bench'.
local M = {}
M.dependencies = { 'ui_imgui' }

M.BENCH_S = 30
-- Extensible list of point-to-point Auto-Benchmark routes (Mode 2: Route Auto-Drive).
-- Maintainers and regional addons can register additional routes via M.registerBenchRoute(route).
M.BENCH_ROUTES = {
  {
    id = 'ventoux_d974',
    name = 'Mont Ventoux D974 Climb (Malaucene -> Hillside)',
    shortName = 'Mont Ventoux D974 (Climb)',
    region = 'Provence',
    startLat = 44.171279, startLon = 5.139169,
    endLat = 44.167000, endLon = 5.175000,
    speedMps = 20.0, -- 72 km/h
    duration = 45,
    stageS = 8,
  },
  {
    id = 'tavel_vineyards',
    name = 'Tavel Vineyards -> Village (Route de la Commanderie)',
    shortName = 'Tavel Vineyards -> Village',
    region = 'Provence',
    startLat = 43.994226, startLon = 4.740771,
    endLat = 44.011161, endLon = 4.701794,
    speedMps = 18.0, -- 65 km/h
    duration = 45,
    stageS = 8,
  },
  {
    id = 'lirac_tavel',
    name = 'Lirac Narrow Streets -> Tavel Vineyards',
    shortName = 'Lirac Streets -> Vineyards',
    region = 'Provence',
    startLat = 44.036874, startLon = 4.690922,
    endLat = 44.011161, endLon = 4.701794,
    speedMps = 18.0, -- 65 km/h
    duration = 45,
    stageS = 8,
  },
  {
    id = 'sault_lavender',
    name = 'Sault Plateau Lavender Fields (D942)',
    shortName = 'Sault Lavender Fields (D942)',
    region = 'Provence',
    startLat = 44.081847, startLon = 5.365593,
    endLat = 44.091500, endLon = 5.355000,
    speedMps = 22.0, -- 80 km/h
    duration = 45,
    stageS = 8,
  },
}

-- Only on the BeamNG.Earth level: the hotkeys, the settings page's Feedback buttons and the frame-time ring do nothing
-- elsewhere (the user, 2026-10-20: the mod should be effectively off on other maps)
M.LEVEL_ID = 'beamng_earth'
local ourLevel = false
local function onLevel() ourLevel = rawget(_G, 'getCurrentLevelIdentifier') ~= nil and getCurrentLevelIdentifier() == M.LEVEL_ID end
M.onClientStartMission = onLevel
function M.onClientEndMission() ourLevel = false end
function M.onExtensionLoaded() if scenetree and scenetree.MissionGroup then onLevel() end end
function M.inOurLevel() return ourLevel end
M.RING = 900            -- frames kept for the "recent" statistics in a report (~10 s at 90 fps)
M.DIR = 'beamngEarth/reports/'
M.SAVED_S = 30          -- the "report saved" window closes itself after this long

local fmt = require('beamngEarth/issuefmt')
local gps = require('beamngEarth/gps')
local im = nil
local ffi = require('ffi')
local form = nil        -- the open report window: { dir, data, kind, titleBuf, noteBuf, frames }
local prof = nil        -- the running profiler: { t0, dur, stage, stageDur, route, fromCef, dts, track, hitches, dir, start, form }
local saved = nil       -- the ImGui "report saved" window: { folder, dir, url, untilT }
local lastSaved = nil   -- persistent last saved report for CEF UI (never cleared by ImGui timer)
local ring, ringN = {}, 0
local toast, toastUntil = nil, 0
local count = 0
local indexed = {}      -- report folders already in index.jsonl (a re-save rewrites the files only)
local lastKind = 'map'

-- wall seconds (os.clock is the process CPU time over all threads: stopwatch.lua)
local wallMs = require('beamngEarth/stopwatch').clock()
local function now() return wallMs() / 1000 end

function M.getIssueRepo()
  return fmt.ISSUE_REPO or fmt.REPO
end

function M.getBenchRoutes()
  return M.BENCH_ROUTES
end

function M.registerBenchRoute(r)
  if type(r) ~= 'table' or type(r.id) ~= 'string' then return false end
  for i, existing in ipairs(M.BENCH_ROUTES) do
    if existing.id == r.id then
      M.BENCH_ROUTES[i] = r
      return true
    end
  end
  M.BENCH_ROUTES[#M.BENCH_ROUTES + 1] = r
  return true
end

local function findRoute(routeId)
  for _, r in ipairs(M.BENCH_ROUTES) do
    if r.id == routeId then return r end
  end
  return M.BENCH_ROUTES[1]
end

local function stats(dts)
  local n = #dts
  if n == 0 then return { frames = 0 } end
  local s = {}
  local sum, mx = 0, 0
  for i = 1, n do s[i] = dts[i]; sum = sum + dts[i]; if dts[i] > mx then mx = dts[i] end end
  table.sort(s)
  local function pct(p) return s[math.max(1, math.ceil(p * n))] end
  local over = { 33, 50, 100 }
  local res = { frames = n, avgMs = sum / n, fps = n / (sum / 1000), p50 = pct(0.5), p95 = pct(0.95),
    p99 = pct(0.99), maxMs = mx }
  for _, o in ipairs(over) do
    local c = 0
    for i = 1, n do if dts[i] > o then c = c + 1 end end
    res['over' .. o] = c
  end
  return res
end
M.stats = stats

local function safe(f, ...)
  local ok, v = pcall(f, ...)
  if ok then return v end
  return 'error: ' .. tostring(v)
end

-- A table's plain values (strings, numbers, booleans), one level: what jsonEncode always takes.
local function scalars(t)
  if type(t) ~= 'table' then return nil end
  local c = {}
  for k, v in pairs(t) do
    local tv = type(v)
    if type(k) == 'string' and (tv == 'string' or tv == 'number' or tv == 'boolean') then c[k] = v end
  end
  return c
end

-- An engine call that may be missing in this game version: nil instead of an error.
local function try(f, ...)
  if type(f) ~= 'function' then return nil end
  local ok, v = pcall(f, ...)
  if ok then return v end
  return nil
end

local function platform(name)
  local P = rawget(_G, 'Engine') and Engine.Platform
  return P and try(P[name])
end

-- What the game can tell about the machine, the game and its graphics settings, the mod and the server
-- (hardware.json).
function M.collectHardware()
  local hw = {}
  hw.os = scalars(platform('getOSInfo'))
  hw.cpu = scalars(platform('getCPUInfo'))
  hw.gpu = scalars(platform('getGPUInfo'))
  local mem = scalars(platform('getMemoryInfo'))
  if mem then hw.mem = { osPhysAvailable = mem.osPhysAvailable, osPhysUsed = mem.osPhysUsed,
    processPhysUsed = mem.processPhysUsed } end
  if hw.os and hw.os.type == 'linux' then hw.os.windowsystem = platform('getVideoDriver') end
  local R = rawget(_G, 'Engine') and Engine.Render
  hw.graphicsApi = R and try(R.getAdapterType)
  local G = rawget(_G, 'GFXDevice')
  hw.videoMode = scalars(G and try(G.getVideoMode))
  hw.desktopVideoMode = try(rawget(_G, 'getDesktopVideoMode'))
  hw.game = { versiond = rawget(_G, 'beamng_versiond'), versionb = rawget(_G, 'beamng_versionb'),
    buildnumber = rawget(_G, 'beamng_buildnumber'), arch = rawget(_G, 'beamng_arch'),
    buildtype = rawget(_G, 'beamng_buildtype') }
  local S = rawget(_G, 'settings')
  if S and type(S.getValue) == 'function' then
    hw.settings = {}
    for _, e in ipairs(fmt.SETTING_KEYS) do
      local v = try(S.getValue, e[1])
      if v ~= nil and type(v) ~= 'table' then hw.settings[e[1]] = v end
    end
  end
  local mm = rawget(_G, 'core_modmanager')
  if mm and try(mm.isReady) then hw.mods = scalars(try(mm.getStats)) end
  local core = rawget(_G, 'beamngEarth_core')
  hw.modVersion = core and core.MOD_VERSION
  hw.server = core and try(core.serverHello) or nil
  local bngSettings = rawget(_G, 'beamngEarth_settings')
  if bngSettings and type(bngSettings.getAll) == 'function' then
    local allS = try(bngSettings.getAll)
    if type(allS) == 'table' then
      hw.effortProfile = allS.effortProfile or 'balanced'
      hw.addonsConfig = {
        addonProvence = allS.addonProvence ~= false,
        sourceIgnRpg = allS.sourceIgnRpg ~= false,
        sourceIgnOrtho = allS.sourceIgnOrtho ~= false,
        sourceIgnBuildings = allS.sourceIgnRpg ~= false,
        sourceProvenceBiomes = allS.sourceProvenceBiomes ~= false,
      }
      local parts = {}
      if allS.addonProvence ~= false then
        parts[#parts + 1] = 'provence=ON'
        parts[#parts + 1] = 'ign_rpg=' .. (allS.sourceIgnRpg ~= false and 'ON' or 'OFF')
        parts[#parts + 1] = 'ign_ortho=' .. (allS.sourceIgnOrtho ~= false and 'ON' or 'OFF')
        parts[#parts + 1] = 'biomes=' .. (allS.sourceProvenceBiomes ~= false and 'ON' or 'OFF')
      else
        parts[#parts + 1] = 'provence=OFF (base global)'
      end
      hw.activeAddons = table.concat(parts, ', ')
    end
  end
  return hw
end

-- Everything the moment can tell: where, what the engine and the mod are doing.
local function capture()
  local d = { time = os.date('%Y-%m-%d %H:%M:%S'), unix = os.time(), level = safe(getCurrentLevelIdentifier) }
  local core = rawget(_G, 'beamngEarth_core')
  if core and core.status then
    local ok, st = pcall(function() return loadstring('return ' .. core.status())() end)
    d.mod = ok and st or tostring(st)
    if ok and type(st) == 'table' and st.player then
      d.lat, d.lon = st.player.lat, st.player.lon
      d.anchorId = st.anchorId
    end
  end
  local veh = getPlayerVehicle and getPlayerVehicle(0)
  if veh then
    local p, v, f = veh:getPosition(), veh:getVelocity(), veh:getDirectionVector()
    d.vehicle = { name = safe(function() return veh:getJBeamFilename() end), pos = { p.x, p.y, p.z },
      speedMs = v:length(), speedMph = v:length() * 2.23694, headingDeg = math.deg(math.atan2(f.x, f.y)) % 360 }
  end
  if core_camera then
    local c = core_camera.getPosition()
    local fw = core_camera.getForward and core_camera.getForward()
    d.camera = { pos = { c.x, c.y, c.z }, forward = fw and { fw.x, fw.y, fw.z } or nil }
  end
  local m = {}
  if Engine.Debug and Engine.Debug.getLastPerformanceMetrics then pcall(Engine.Debug.getLastPerformanceMetrics, m) end
  d.engineMetrics = m
  d.fpsLimit = safe(function() return Engine.getCurrentFpsLimitReason and Engine.getCurrentFpsLimitReason() end)
  d.vram = safe(function() return Engine.Render and Engine.Render.getVRAMUsage and Engine.Render.getVRAMUsage() end)
  local recent = {}
  for i = 1, math.min(ringN, M.RING) do recent[#recent + 1] = ring[i] end
  d.recentFrames = stats(recent)
  return d
end

local function newDir(kind)
  count = count + 1
  local rel = M.DIR .. os.date('%Y%m%d_%H%M%S') .. '_' .. kind .. '_' .. count .. '/'
  if not FS:directoryExists(rel) then FS:directoryCreate(rel, true) end
  return rel
end

local function screenshot(rel)
  if type(createScreenshot2) ~= 'function' then return nil end
  local ok = pcall(createScreenshot2, { filename = rel .. 'screenshot', writeJPG = true, superSampling = 1 })
  return ok and (FS:getUserPath() .. rel .. 'screenshot.jpg'):gsub('\\', '/') or nil
end

local function encode(t)
  local ok, s = pcall(jsonEncodePretty or jsonEncode, t)
  if ok and s then return s end
  return jsonEncode(t)
end

-- Open a GitHub issue URL via the companion server (`open_page`), bypassing BeamNG 0.40's C++ domain filter.
-- Never overwrites the user's clipboard automatically; use M.copyLastReport() for explicit clipboard copy.
function M.openIssueUrl(url)
  if type(url) ~= 'string' or url == '' then return false end
  local core = rawget(_G, 'beamngEarth_core')
  if core and type(core.openPage) == 'function' then
    return core.openPage(url)
  end
  if openWebBrowser then
    pcall(openWebBrowser, url)
    return true
  end
  return false
end

-- Recover `lastSaved` from the latest entry in `beamngEarth/reports/index.jsonl` if `lastSaved` is nil
-- (for example after an extension reload or game restart).
local function ensureLastSaved()
  if lastSaved and lastSaved.dir then return lastSaved end
  local idx = readFile(M.DIR .. 'index.jsonl')
  if not idx or idx == '' then return nil end
  local lastLine = nil
  for line in idx:gmatch('[^\r\n]+') do
    if line:match('%S') then lastLine = line end
  end
  if not lastLine then return nil end
  local ok, entry = pcall(jsonDecode, lastLine)
  if not ok or type(entry) ~= 'table' or type(entry.folder) ~= 'string' then return nil end
  local folder = entry.folder:gsub('\\', '/')
  local rel = folder:match('([Bb]eam[Nn][Gg][Ee]arth/reports/[^/]+/?)$')
  if not rel then return nil end
  if not rel:match('/$') then rel = rel .. '/' end
  local md = readFile(rel .. 'issue.md')
  local repRaw = readFile(rel .. 'report.json')
  local okR, repData = pcall(function() return repRaw and jsonDecode(repRaw) or nil end)
  local summary = nil
  if okR and type(repData) == 'table' then
    summary = repData.bench and fmt.framesLine(repData.bench) or (repData.recentFrames and fmt.framesLine(repData.recentFrames))
  end
  if not summary and type(entry.fps) == 'number' then
    summary = string.format('%.1f fps avg', entry.fps)
  end
  local url = nil
  if md and md ~= '' then
    local k = fmt.kind(entry.kind or 'perf')
    local title, body = fmt.splitIssue(md)
    url = fmt.issueUrl(title, body, k.label, fmt.URL_MAX, M.getIssueRepo())
  end
  lastSaved = {
    folder = folder,
    dir = rel,
    url = url,
    issueMd = md,
    summary = summary,
    kind = fmt.kind(entry.kind or 'perf').name,
    repo = M.getIssueRepo(),
  }
  return lastSaved
end

local function write(rel, data, quiet)
  data.folder = (FS:getUserPath() .. rel):gsub('\\', '/')
  writeFile(rel .. 'report.json', encode(data))
  local okH, hw = pcall(M.collectHardware)
  if not okH then hw = { error = tostring(hw) } end
  pcall(writeFile, rel .. 'hardware.json', encode(hw))
  local okI, issue = pcall(fmt.buildIssue, data, hw)
  if okI then pcall(writeFile, rel .. 'issue.md', issue) else log('W', 'beamngEarth', 'issue.md: ' .. tostring(issue)) end
  if not indexed[rel] then
    indexed[rel] = true
    local line = jsonEncode({ time = data.time, kind = data.kind, folder = data.folder, lat = data.lat, lon = data.lon,
      title = data.title, note = data.note,
      fps = data.bench and data.bench.fps or (data.recentFrames and data.recentFrames.fps) })
    local idx = M.DIR .. 'index.jsonl'
    local old = readFile(idx) or ''
    writeFile(idx, old .. line .. '\n')
  end
  log('I', 'beamngEarth', 'report saved: ' .. data.folder)
  local url = nil
  if okI then
    local k = fmt.kind(data.kind)
    local title, body = fmt.splitIssue(issue)
    url = fmt.issueUrl(title, body, k.label, fmt.URL_MAX, M.getIssueRepo())
  end
  local summary = data.bench and fmt.framesLine(data.bench) or (data.recentFrames and fmt.framesLine(data.recentFrames)) or nil
  lastSaved = {
    folder = data.folder,
    dir = rel,
    url = url,
    issueMd = okI and issue or nil,
    summary = summary,
    mode = data.benchMode or 'free',
    routeName = data.route and (data.route.shortName or data.route.name) or nil,
    repo = M.getIssueRepo(),
    kind = fmt.kind(data.kind).name,
  }
  if quiet then return end
  saved = { folder = data.folder, dir = rel, url = url, issueMd = okI and issue or nil, summary = summary,
    untilT = now() + M.SAVED_S, kind = fmt.kind(data.kind).name }
end

local function openForm(rel, data, kind)
  form = { dir = rel, data = data, kind = kind or lastKind, titleBuf = nil, noteBuf = nil, frames = 0 }
end

-- Ctrl+Shift+E: capture now, open the report window.
function M.note()
  if form or not ourLevel then return end
  if prof then M.profilerAttach() return end
  local rel = newDir('report')
  local data = capture()
  data.screenshot = screenshot(rel)       -- the view the player saw (the window opens next frame)
  saved = nil
  openForm(rel, data)
end

-- Ctrl+Shift+Y: the performance profiler over the next BENCH_S seconds. With the report window open,
-- the profile goes into that report (kind Performance issue).
function M.profiler(seconds)
  if prof or not ourLevel then return end
  local rel, start, pending
  if form then
    rel, start, pending = form.dir, form.data, form
    pending.kind = 'perf'
    form = nil
  else
    rel = newDir('profile')
    start = capture()
    start.screenshot = screenshot(rel)
  end
  prof = { t0 = now(), dur = tonumber(seconds) or M.BENCH_S, stage = 'recording', dts = {}, track = {}, hitches = {},
    dir = rel, lastSample = -1, start = start, form = pending }
  toast, toastUntil = string.format('Performance profiler: recording %d s (keep driving)', prof.dur), now() + 3
end
M.benchmark = M.profiler   -- the input action (beamngEarth_reportBench) and older console calls

-- Ctrl+Shift+E while the profiler runs: the report window opens when it ends.
function M.profilerAttach()
  if prof and not prof.form then prof.form = { kind = 'perf' } end
  toast, toastUntil = 'The report window opens when the profiler ends', now() + 3
end

local function stopRouteAutodrive()
  pcall(function()
    gps.speedOverride = nil
    if gps.autodrive and gps.autodrive() then gps.setAutodrive(false) end
    gps.clear()
    local veh = getPlayerVehicle and getPlayerVehicle(0)
    if veh then veh:queueLuaCommand('ai.setMode("disabled")') end
  end)
end

local function computeTrackDistance(track)
  local dist = 0
  local prev = nil
  for _, s in ipairs(track or {}) do
    local p = s.pos
    if type(p) == 'table' and p[1] and p[2] then
      if prev then
        local dx, dy = p[1] - prev[1], p[2] - prev[2]
        local step = math.sqrt(dx * dx + dy * dy)
        if step < 250 then dist = dist + step end
      end
      prev = p
    end
  end
  return dist
end

local function finishProf(b, elapsedS)
  if b.route then stopRouteAutodrive() end
  local data = b.start or capture()
  data.kind = 'perf'
  data.benchMode = b.mode or (b.route and 'route' or 'free')
  if b.route then
    data.route = {
      id = b.route.id,
      name = b.route.name,
      shortName = b.route.shortName,
      startLat = b.route.startLat,
      startLon = b.route.startLon,
      endLat = b.route.endLat,
      endLon = b.route.endLon,
      speedMps = b.route.speedMps,
      distanceDrivenM = computeTrackDistance(b.track),
    }
  end
  data.bench = stats(b.dts)
  data.bench.seconds = elapsedS
  data.bench.hitches = b.hitches
  data.track = b.track
  data.endState = capture()
  prof = nil
  local f = b.form
  if b.fromCef then
    -- Started from the CEF Generation Addons window: write files & update lastSaved quietly without popping ImGui
    write(b.dir, data, true)
  elseif f and f.data then
    write(b.dir, data, false)
  else
    write(b.dir, data, true)
    openForm(b.dir, data, 'perf')
    toast, toastUntil = 'Performance profiler done: add a title and Save', now() + 4
  end
end

local function profFrame(dtMs)
  local b = prof
  local t = now() - b.t0
  if b.stage == 'staging' then
    local stageDur = b.stageDur or 8
    if t >= stageDur then
      -- Transition from route staging to active recording + autodrive
      b.stage = 'recording'
      b.t0 = now()
      b.lastSample = -1
      b.start = capture()
      b.start.screenshot = screenshot(b.dir)
      b.start.kind = 'perf'
      b.start.title = b.title
      b.start.note = b.note
      if b.route then
        pcall(function()
          gps.speedOverride = b.route.speedMps or 20.0
          gps.setDestination(b.route.endLat, b.route.endLon, b.route.shortName or b.route.name)
          gps.setAutodrive(true)
        end)
      end
    end
    return
  end

  b.dts[#b.dts + 1] = dtMs
  local core = rawget(_G, 'beamngEarth_core')
  if dtMs > 50 then
    local veh = getPlayerVehicle and getPlayerVehicle(0)
    local p = veh and veh:getPosition()
    b.hitches[#b.hitches + 1] = { t = t, ms = dtMs, pos = p and { p.x, p.y, p.z } or nil }
  end
  if math.floor(t) > b.lastSample then
    b.lastSample = math.floor(t)
    local veh = getPlayerVehicle and getPlayerVehicle(0)
    local p = veh and veh:getPosition()
    local s = { t = math.floor(t), pos = p and { p.x, p.y, p.z } or nil,
      speedMph = veh and veh:getVelocity():length() * 2.23694 or nil }
    if core and core.status then
      local ok, st = pcall(function() return loadstring('return ' .. core.status())() end)
      if ok and type(st) == 'table' then
        s.lat, s.lon = st.player and st.player.lat, st.player and st.player.lon
        s.far = st.far and { live = st.far.live, queued = st.far.queued } or nil
        s.trees = st.trees and st.trees.items or nil
        s.sea = st.sea and st.sea.tiles or nil
      end
    end
    local m = {}
    if Engine.Debug and Engine.Debug.getLastPerformanceMetrics then pcall(Engine.Debug.getLastPerformanceMetrics, m) end
    s.metrics = m
    b.track[#b.track + 1] = s
    -- Check if route autodrive reached the destination early
    if b.route and t > 5 then
      local gst = gps.status and gps.status()
      if not gst or (gst.remaining and gst.remaining < 35) then
        finishProf(b, t)
        return
      end
    end
  end
  if t >= b.dur then
    finishProf(b, t)
  end
end

local function formText(f)
  if f.titleBuf then f.data.title = ffi.string(f.titleBuf) end
  if f.noteBuf then f.data.note = ffi.string(f.noteBuf) end
  f.data.kind = f.kind
  lastKind = f.kind
end

-- Save the open report with this text (tests, the console). kind: map / perf / bug / idea.
function M.saveNote(text, kind, title)
  if not form then M.note() end
  if not form then return end
  form.data.note = tostring(text or '')
  form.data.title = title and tostring(title) or form.data.title
  form.data.kind = kind or form.kind
  write(form.dir, form.data)
  form = nil
end

function M.status()
  local ls = ensureLastSaved()
  local stStage = prof and (prof.stage or 'recording') or nil
  local stDur = prof and (stStage == 'staging' and (prof.stageDur or 8) or prof.dur) or M.BENCH_S
  return {
    formOpen = form ~= nil,
    noteOpen = form ~= nil,
    profilerRunning = prof ~= nil,
    benchRunning = prof ~= nil,
    stage = stStage,
    mode = prof and prof.mode or (ls and ls.mode) or 'free',
    routeName = prof and prof.route and (prof.route.shortName or prof.route.name) or (ls and ls.routeName) or nil,
    saved = count,
    lastFolder = ls and ls.folder or nil,
    elapsed = prof and math.max(0, math.floor(now() - prof.t0)) or 0,
    duration = stDur,
    lastSummary = ls and ls.summary or nil,
    lastUrl = ls and ls.url or nil,
    issueRepo = M.getIssueRepo(),
    routes = M.BENCH_ROUTES,
  }
end

-- Start a benchmark from the CEF Generation Addons UI:
--   mode: 'free' (30s free drive) or 'route' (point-to-point route autodrive)
--   arg: duration seconds (for 'free') or routeId string (for 'route')
function M.uiStartBench(mode, arg)
  onLevel()
  if not ourLevel then return { ok = false, error = 'Not in BeamNG.Earth level' } end
  if prof then return { ok = true, alreadyRunning = true } end
  if type(mode) == 'number' then
    arg = mode
    mode = 'free'
  end
  mode = (mode == 'route') and 'route' or 'free'

  local bngSettings = rawget(_G, 'beamngEarth_settings')
  local allS = bngSettings and bngSettings.getAll and bngSettings.getAll() or {}
  local addonTag = (allS.addonProvence ~= false) and 'provence=ON' or 'provence=OFF'
  local effortTag = tostring(allS.effortProfile or 'balanced')
  local rel = newDir('profile')
  saved = nil -- ensure old ImGui saved box is closed

  if mode == 'route' then
    local route = findRoute(tostring(arg or 'ventoux_d974'))
    local core = rawget(_G, 'beamngEarth_core')
    if core and core.teleport then
      pcall(core.teleport, route.startLat, route.startLon, route.shortName or route.name, { record = false })
    end
    pcall(function()
      gps.speedOverride = route.speedMps or 20.0
      gps.setDestination(route.endLat, route.endLon, route.shortName or route.name)
    end)
    local title = string.format('Route Benchmark: %s (%s, effort=%s)', route.shortName or route.id, addonTag, effortTag)
    local note = string.format('Automated point-to-point route benchmark on %s (%.5f, %.5f -> %.5f, %.5f, target %.0f km/h, %s, effortProfile=%s).',
      route.name, route.startLat, route.startLon, route.endLat, route.endLon, (route.speedMps or 20) * 3.6, addonTag, effortTag)
    prof = {
      t0 = now(),
      dur = tonumber(route.duration) or 45,
      stage = 'staging',
      stageDur = tonumber(route.stageS) or 8,
      mode = 'route',
      route = route,
      fromCef = true,
      title = title,
      note = note,
      dts = {},
      track = {},
      hitches = {},
      dir = rel,
      lastSample = -1,
    }
    return { ok = true, mode = 'route', route = route.shortName or route.name, duration = prof.dur, stageDur = prof.stageDur }
  end

  local dur = tonumber(arg) or M.BENCH_S
  local start = capture()
  start.screenshot = screenshot(rel)
  start.kind = 'perf'
  start.benchMode = 'free'
  start.title = string.format('Benchmark (%s, effort=%s)', addonTag, effortTag)
  start.note = string.format('Automated %ds in-game free-drive performance benchmark ticket (%s, effortProfile=%s).', dur, addonTag, effortTag)
  prof = {
    t0 = now(),
    dur = dur,
    stage = 'recording',
    mode = 'free',
    fromCef = true,
    dts = {},
    track = {},
    hitches = {},
    dir = rel,
    lastSample = -1,
    start = start,
    form = { data = start, kind = 'perf' },
  }
  return { ok = true, mode = 'free', duration = prof.dur }
end

function M.uiStopBench()
  if not prof then return { ok = false } end
  local b = prof
  local elapsed = math.max(1, now() - b.t0)
  if b.stage == 'staging' or #b.dts < 10 then
    if b.route then stopRouteAutodrive() end
    prof = nil
    return { ok = true, cancelled = true }
  end
  finishProf(b, elapsed)
  return { ok = true, stoppedEarly = true }
end

function M.openLastFolder()
  local ls = ensureLastSaved()
  if ls and ls.dir and Engine and Engine.Platform and Engine.Platform.exploreFolder then
    pcall(Engine.Platform.exploreFolder, '/' .. ls.dir)
    return { ok = true, folder = ls.folder }
  end
  return { ok = false, error = 'No saved report folder found' }
end

function M.openLastIssueUrl()
  local ls = ensureLastSaved()
  if ls and ls.url then
    local ok = M.openIssueUrl(ls.url)
    return { ok = ok, repo = ls.repo or M.getIssueRepo(), url = ls.url }
  end
  return { ok = false, error = 'No saved report ticket found' }
end

function M.copyLastReport()
  local ls = ensureLastSaved()
  if not ls then return { ok = false, error = 'No saved report found' } end
  local md = ls.issueMd or (ls.dir and readFile(ls.dir .. 'issue.md')) or nil
  if type(md) == 'string' and md ~= '' and setClipboard then
    pcall(setClipboard, md)
    return { ok = true, bytes = #md }
  end
  return { ok = false, error = 'Clipboard unavailable or issue.md empty' }
end

function M.onPreRender(dtReal)
  if not ourLevel or not dtReal or dtReal <= 0 then return end
  local ms = dtReal * 1000
  ringN = ringN + 1
  ring[(ringN - 1) % M.RING + 1] = ms
  if prof then profFrame(ms) end
end

local function wrapped(s)
  im.PushTextWrapPos(0)
  im.TextUnformatted(tostring(s))
  im.PopTextWrapPos()
end

local function drawSaved()
  if not saved then return end
  if now() > saved.untilT then saved = nil return end
  im.SetNextWindowSize(im.ImVec2(560, 0), im.Cond_FirstUseEver)
  if im.Begin('BeamNG.Earth report saved##bngeSaved', nil, im.WindowFlags_AlwaysAutoResize) then
    im.TextUnformatted(saved.kind .. ' report saved in:')
    im.TextUnformatted(saved.folder)
    wrapped('issue.md there is a ready-to-post GitHub issue: edit it, then post it with the screenshot '
      .. '(or run: python3 tools/reports.py issue).')
    if im.Button('Open folder') then
      pcall(Engine.Platform.exploreFolder, '/' .. saved.dir)
      saved.untilT = now() + M.SAVED_S
    end
    if saved.url then
      im.SameLine()
      if im.Button('Open GitHub issue page') then
        M.openIssueUrl(saved.url)
        saved.untilT = now() + M.SAVED_S
      end
    end
    im.SameLine()
    if im.Button('Close') then saved = nil end
  end
  im.End()
end

local function drawForm()
  local f = form
  f.frames = f.frames + 1
  if not f.titleBuf then
    f.titleBuf = im.ArrayChar(128, f.data.title or '')
    f.noteBuf = im.ArrayChar(4096, f.data.note or '')
  end
  im.SetNextWindowSize(im.ImVec2(560, 360), im.Cond_FirstUseEver)
  if im.Begin('BeamNG.Earth report##bngeNote', nil, 0) then
    im.TextUnformatted(string.format('%s  |  %s', f.data.time or '',
      f.data.lat and string.format('%.5f, %.5f', f.data.lat, f.data.lon) or 'no location'))
    for i, k in ipairs(fmt.KINDS) do
      if i > 1 then im.SameLine() end
      if im.RadioButton1(k.name .. '##bngeKind' .. i, f.kind == k.id) then f.kind = k.id end
    end
    wrapped(fmt.kind(f.kind).hint)
    im.TextUnformatted('Title:')
    if f.frames == 2 then im.SetKeyboardFocusHere() end
    im.PushItemWidth(-1)
    im.InputText('##bngeTitle', f.titleBuf, im.GetLengthArrayCharPtr(f.titleBuf))
    im.PopItemWidth()
    im.TextUnformatted('Description:')
    im.InputTextMultiline('##bngeNoteText', f.noteBuf, im.GetLengthArrayCharPtr(f.noteBuf), im.ImVec2(-1, 130))
    local b = f.data.bench
    if b and b.fps then
      im.TextUnformatted('Performance profiler: ' .. (fmt.framesLine(b) or ''))
    end
    if im.Button('Save report') then
      formText(f)
      write(f.dir, f.data)
      form = nil
    end
    if form and f.kind == 'perf' and not b then
      im.SameLine()
      if im.Button(string.format('Save + record %d s profile', M.BENCH_S)) then
        formText(f)
        M.profiler()
      end
    end
    im.SameLine()
    if form and im.Button(b and 'Close (keep the profile)' or 'Cancel') then form = nil end
  end
  im.End()
end

function M.onUpdate()
  im = im or rawget(_G, 'ui_imgui')
  if not im then return end
  if toast and now() < toastUntil then
    im.SetNextWindowPos(im.ImVec2(20, 120), im.Cond_Always)
    if im.Begin('##bngeReportToast', nil, im.WindowFlags_NoDecoration + im.WindowFlags_AlwaysAutoResize
        + im.WindowFlags_NoInputs) then
      im.TextUnformatted(toast)
    end
    im.End()
  end
  if prof and not prof.fromCef then
    im.SetNextWindowPos(im.ImVec2(20, 160), im.Cond_Always)
    if im.Begin('##bngeBench', nil, im.WindowFlags_NoDecoration + im.WindowFlags_AlwaysAutoResize
        + im.WindowFlags_NoInputs) then
      im.TextUnformatted(string.format('Performance profiler: %.0f / %d s', now() - prof.t0, prof.dur))
    end
    im.End()
  end
  drawSaved()
  if form then drawForm() end
end

return M
