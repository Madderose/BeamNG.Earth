// Standalone floating "Generation Addons" window in the CEF UI layer.
// Single-instance, in-place DOM updates (never rebuilds innerHTML on a timer, never resets drag position),
// with Minimize ("Min"), Close ("X"), Refresh World, and integrated 30s Hardware/Addon Benchmark Ticket controls.

const ROOT_ID = "bng-earth-addons-floating-root"
const STYLE_ID = "bng-earth-addons-floating-style"

const EFFORT_PROFILES = [
  { id: "low", label: "Low" },
  { id: "balanced", label: "Balanced" },
  { id: "high", label: "High" },
  { id: "ultra", label: "Ultra" },
  { id: "auto_fps", label: "Auto-FPS" },
]

function getState() {
  if (!window.__bngEarthAddonsState) {
    window.__bngEarthAddonsState = {
      visible: true,
      minimized: false,
      addonProvence: true,
      sourceIgnRpg: true,
      sourceIgnOrtho: true,
      sourceProvenceBiomes: true,
      effortProfile: "balanced",
      note: "",
      benchRunning: false,
      benchElapsed: 0,
      benchDuration: 30,
      benchSummary: "",
      benchFolder: "",
      benchHasUrl: false,
      benchPollTimer: null,
      posX: 28,
      posY: 84,
      noteTimer: null,
    }
  }
  return window.__bngEarthAddonsState
}

function engineLua(code, cb) {
  if (window.bngApi && window.bngApi.engineLua) {
    window.bngApi.engineLua(code, cb)
  }
}

function injectStyles() {
  let style = document.getElementById(STYLE_ID)
  if (!style) {
    style = document.createElement("style")
    style.id = STYLE_ID
    document.head.appendChild(style)
  }
  style.textContent = `
    #${ROOT_ID} {
      position: fixed;
      z-index: 99999;
      font-family: "Overpass", "Noto Sans", sans-serif;
      color: #f0f2f5;
      user-select: none;
      pointer-events: auto;
    }
    .bng-earth-addons-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(20, 24, 30, 0.92);
      border: 1px solid rgba(255, 102, 0, 0.65);
      border-radius: 6px;
      padding: 6px 12px;
      color: #fff;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.55);
    }
    .bng-earth-addons-pill:hover {
      background: rgba(34, 40, 50, 0.96);
      border-color: #ff6600;
    }
    .bng-earth-addons-card {
      width: 368px;
      background: rgba(20, 24, 30, 0.94);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.68);
      padding: 12px 14px 14px;
      backdrop-filter: blur(6px);
    }
    .bng-earth-addons-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 10px;
      margin-bottom: 8px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      cursor: move;
    }
    .bng-earth-addons-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 16px;
      font-weight: 700;
      font-style: italic;
      color: #ffffff;
    }
    .bng-earth-addons-slash {
      display: inline-block;
      width: 6px;
      height: 18px;
      background: #ff6600;
      transform: skewX(-16deg);
    }
    .bng-earth-addons-hdrbtns {
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .bng-earth-addons-hdrbtn {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.16);
      color: #ddd;
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 12px;
      line-height: 1.3;
      cursor: pointer;
    }
    .bng-earth-addons-hdrbtn:hover {
      background: rgba(255, 102, 0, 0.25);
      border-color: #ff6600;
      color: #fff;
    }
    .bng-earth-addons-hdrbtn.close:hover {
      background: rgba(220, 50, 50, 0.8);
      border-color: #ff5555;
      color: #fff;
    }
    .bng-earth-addons-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(38, 44, 54, 0.85);
      border-radius: 5px;
      padding: 8px 10px;
      margin-bottom: 6px;
      font-size: 13px;
      cursor: pointer;
    }
    .bng-earth-addons-row.sub {
      padding-left: 20px;
      background: rgba(30, 35, 44, 0.8);
      font-size: 12.5px;
      color: #d6dce5;
    }
    .bng-earth-addons-row:hover {
      background: rgba(50, 58, 70, 0.92);
    }
    .bng-earth-switch {
      width: 34px;
      height: 18px;
      border-radius: 10px;
      background: rgba(120, 130, 145, 0.55);
      position: relative;
      flex-shrink: 0;
      transition: background 0.15s ease;
    }
    .bng-earth-switch.on {
      background: #ff6600;
    }
    .bng-earth-switch::after {
      content: "";
      position: absolute;
      top: 2px;
      left: 2px;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #ffffff;
      transition: transform 0.15s ease;
    }
    .bng-earth-switch.on::after {
      transform: translateX(16px);
    }
    .bng-earth-effort-box {
      background: rgba(38, 44, 54, 0.85);
      border-radius: 5px;
      padding: 8px 10px;
      margin-bottom: 8px;
    }
    .bng-earth-effort-label {
      font-size: 12px;
      color: #b8c2d0;
      margin-bottom: 6px;
    }
    .bng-earth-effort-pills {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 4px;
    }
    .bng-earth-effort-btn {
      background: rgba(20, 24, 30, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #cfd6e0;
      border-radius: 4px;
      padding: 4px 2px;
      font-size: 11px;
      text-align: center;
      cursor: pointer;
    }
    .bng-earth-effort-btn.active {
      background: #ff6600;
      border-color: #ff6600;
      color: #fff;
      font-weight: 700;
    }
    .bng-earth-actions-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
    }
    .bng-earth-refresh-btn {
      width: 100%;
      background: rgba(255, 102, 0, 0.18);
      border: 1px solid #ff6600;
      color: #ffffff;
      border-radius: 5px;
      padding: 7px 8px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
    }
    .bng-earth-refresh-btn:hover {
      background: #ff6600;
    }
    .bng-earth-bench-btn {
      width: 100%;
      background: rgba(56, 139, 253, 0.18);
      border: 1px solid rgba(88, 166, 255, 0.8);
      color: #e6f0ff;
      border-radius: 5px;
      padding: 7px 8px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
    }
    .bng-earth-bench-btn:hover {
      background: rgba(56, 139, 253, 0.45);
      border-color: #79c0ff;
    }
    .bng-earth-bench-btn.running {
      background: rgba(255, 153, 0, 0.28);
      border-color: #ffaa00;
      color: #fff;
    }
    .bng-earth-bench-result {
      margin-top: 8px;
      padding: 8px 10px;
      background: rgba(26, 32, 42, 0.92);
      border: 1px solid rgba(88, 166, 255, 0.45);
      border-radius: 5px;
      font-size: 11.5px;
      color: #d6e4f5;
    }
    .bng-earth-bench-result-btns {
      display: flex;
      gap: 6px;
      margin-top: 6px;
    }
    .bng-earth-bench-subbtn {
      flex: 1;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.22);
      color: #fff;
      border-radius: 4px;
      padding: 4px 6px;
      font-size: 11px;
      cursor: pointer;
      text-align: center;
    }
    .bng-earth-bench-subbtn:hover {
      background: rgba(255, 102, 0, 0.35);
      border-color: #ff6600;
    }
    .bng-earth-addons-note {
      font-size: 11.5px;
      color: #ff9944;
      text-align: center;
      margin-top: 6px;
      min-height: 15px;
    }
  `
}

function setNote(text, clearMs = 2500) {
  const st = getState()
  st.note = text
  updateDOM()
  if (st.noteTimer) clearTimeout(st.noteTimer)
  if (text && clearMs > 0) {
    st.noteTimer = setTimeout(() => {
      st.note = ""
      updateDOM()
    }, clearMs)
  }
}

export function syncFromLua() {
  engineLua("beamngEarth_settings and beamngEarth_settings.getAll() or nil", res => {
    if (!res) return
    const st = getState()
    st.addonProvence = res.addonProvence !== false
    st.sourceIgnRpg = res.sourceIgnRpg !== false
    st.sourceIgnOrtho = res.sourceIgnOrtho !== false
    st.sourceProvenceBiomes = res.sourceProvenceBiomes !== false
    st.effortProfile = res.effortProfile || "balanced"
    updateDOM()
  })
}

function pollBenchStatus() {
  engineLua("beamngEarth_report and beamngEarth_report.status() or nil", stRes => {
    const st = getState()
    if (!stRes) return
    const wasRunning = st.benchRunning
    st.benchRunning = !!stRes.benchRunning
    st.benchElapsed = stRes.elapsed || 0
    st.benchDuration = stRes.duration || 30
    if (stRes.lastSummary) st.benchSummary = stRes.lastSummary
    if (stRes.lastFolder) st.benchFolder = stRes.lastFolder
    st.benchHasUrl = !!stRes.lastUrl
    if (wasRunning && !st.benchRunning) {
      if (st.benchPollTimer) {
        clearInterval(st.benchPollTimer)
        st.benchPollTimer = null
      }
      setNote("30s Benchmark saved to report.json & issue.md!", 4500)
    }
    updateDOM()
  })
}

function startBenchmark() {
  const st = getState()
  if (st.benchRunning) return
  engineLua("beamngEarth_report and beamngEarth_report.uiStartBench(30) or nil", res => {
    if (!res || !res.ok) {
      setNote((res && res.error) || "Load BeamNG.Earth level first", 3500)
      return
    }
    st.benchRunning = true
    st.benchElapsed = 0
    st.benchDuration = res.duration || 30
    setNote("Recording 30s benchmark (keep driving)...", 0)
    if (st.benchPollTimer) clearInterval(st.benchPollTimer)
    st.benchPollTimer = setInterval(pollBenchStatus, 500)
    updateDOM()
  })
}

function openBenchFolder() {
  engineLua("beamngEarth_report and beamngEarth_report.openLastFolder() or nil")
}

function openBenchIssue() {
  engineLua("beamngEarth_report and beamngEarth_report.openLastIssueUrl() or nil")
}

function toggleBool(key) {
  const st = getState()
  st[key] = !st[key]
  setNote("Applying & refreshing world...", 0)
  engineLua(`beamngEarth_settings and beamngEarth_settings.uiSet(${JSON.stringify(key)}, ${st[key] ? "true" : "false"}) or nil`, () => {
    setNote("Updated", 2000)
  })
}

function setEffort(id) {
  const st = getState()
  st.effortProfile = id
  setNote(`Effort profile: ${id}...`, 0)
  engineLua(`beamngEarth_settings and beamngEarth_settings.uiSet("effortProfile", ${JSON.stringify(id)}) or nil`, () => {
    setNote(`Effort: ${id}`, 2000)
  })
}

function triggerRefresh() {
  setNote("Refreshing nearby vegetation & buildings...", 0)
  engineLua("beamngEarth_settings and beamngEarth_settings.uiRefreshWorld() or nil", () => {
    setNote("World refresh triggered", 2500)
  })
}

function attachDrag(headerEl, rootEl) {
  let dragging = false
  let startX = 0, startY = 0, origX = 0, origY = 0
  headerEl.addEventListener("mousedown", e => {
    if (e.target.tagName === "BUTTON") return
    const st = getState()
    dragging = true
    startX = e.clientX
    startY = e.clientY
    origX = st.posX
    origY = st.posY
    const onMove = ev => {
      if (!dragging) return
      st.posX = Math.max(8, Math.min(window.innerWidth - 375, origX + (ev.clientX - startX)))
      st.posY = Math.max(8, Math.min(window.innerHeight - 80, origY + (ev.clientY - startY)))
      rootEl.style.left = `${st.posX}px`
      rootEl.style.top = `${st.posY}px`
    }
    const onUp = () => {
      dragging = false
      window.removeEventListener("mousemove", onMove)
      window.removeEventListener("mouseup", onUp)
    }
    window.addEventListener("mousemove", onMove)
    window.addEventListener("mouseup", onUp)
  })
}

function buildDOMOnce() {
  injectStyles()
  let root = document.getElementById(ROOT_ID)
  if (root) root.remove()
  const st = getState()
  root = document.createElement("div")
  root.id = ROOT_ID
  root.style.left = `${st.posX}px`
  root.style.top = `${st.posY}px`

  const effortBtns = EFFORT_PROFILES.map(p => `
    <button class="bng-earth-effort-btn" data-effort="${p.id}">${p.label}</button>
  `).join("")

  root.innerHTML = `
    <div class="bng-earth-addons-pill" id="bng-earth-addons-pill-view" style="display:none;">
      <span class="bng-earth-addons-slash"></span>
      <span id="bng-earth-addons-pill-text">Generation Addons (ON)</span>
      <button class="bng-earth-addons-hdrbtn close" id="bng-earth-addons-pill-close" title="Close">X</button>
    </div>
    <div class="bng-earth-addons-card" id="bng-earth-addons-card-view">
      <div class="bng-earth-addons-header" id="bng-earth-addons-drag">
        <div class="bng-earth-addons-title">
          <span class="bng-earth-addons-slash"></span>
          <span>Generation Addons</span>
        </div>
        <div class="bng-earth-addons-hdrbtns">
          <button class="bng-earth-addons-hdrbtn" id="bng-earth-addons-min" title="Minimize to pill">Min</button>
          <button class="bng-earth-addons-hdrbtn close" id="bng-earth-addons-close" title="Close window">X</button>
        </div>
      </div>
      <div class="bng-earth-addons-row" data-key="addonProvence">
        <span>France & Provence Ground Truth Pack</span>
        <div class="bng-earth-switch" data-switch="addonProvence"></div>
      </div>
      <div id="bng-earth-addons-subrows">
        <div class="bng-earth-addons-row sub" data-key="sourceIgnRpg">
          <span>- IGN BD TOPO & RPG Parcels</span>
          <div class="bng-earth-switch" data-switch="sourceIgnRpg"></div>
        </div>
        <div class="bng-earth-addons-row sub" data-key="sourceIgnOrtho">
          <span>- IGN 20 cm Orthophoto Roof Tinting</span>
          <div class="bng-earth-switch" data-switch="sourceIgnOrtho"></div>
        </div>
        <div class="bng-earth-addons-row sub" data-key="sourceProvenceBiomes">
          <span>- Provence Crops & Biomes</span>
          <div class="bng-earth-switch" data-switch="sourceProvenceBiomes"></div>
        </div>
      </div>
      <div class="bng-earth-effort-box">
        <div class="bng-earth-effort-label">Ground-Truth Effort Profile (Layer B)</div>
        <div class="bng-earth-effort-pills">${effortBtns}</div>
      </div>
      <div class="bng-earth-actions-grid">
        <button class="bng-earth-refresh-btn" id="bng-earth-addons-refresh">Refresh World</button>
        <button class="bng-earth-bench-btn" id="bng-earth-addons-bench">Benchmark (30s)</button>
      </div>
      <div class="bng-earth-bench-result" id="bng-earth-bench-result" style="display:none;">
        <div id="bng-earth-bench-summary"></div>
        <div class="bng-earth-bench-result-btns">
          <button class="bng-earth-bench-subbtn" id="bng-earth-bench-folder">Open Folder</button>
          <button class="bng-earth-bench-subbtn" id="bng-earth-bench-issue">Post GitHub Ticket</button>
        </div>
      </div>
      <div class="bng-earth-addons-note" id="bng-earth-addons-note"></div>
    </div>
  `
  document.body.appendChild(root)

  attachDrag(root.querySelector("#bng-earth-addons-drag"), root)

  root.querySelector("#bng-earth-addons-min").addEventListener("click", e => {
    e.stopPropagation()
    st.minimized = true
    updateDOM()
  })
  root.querySelector("#bng-earth-addons-close").addEventListener("click", e => {
    e.stopPropagation()
    st.visible = false
    updateDOM()
  })
  root.querySelector("#bng-earth-addons-pill-view").addEventListener("click", e => {
    if (e.target.id === "bng-earth-addons-pill-close") return
    st.minimized = false
    syncFromLua()
    updateDOM()
  })
  root.querySelector("#bng-earth-addons-pill-close").addEventListener("click", e => {
    e.stopPropagation()
    st.visible = false
    updateDOM()
  })

  root.querySelectorAll(".bng-earth-addons-row").forEach(row => {
    row.addEventListener("click", () => toggleBool(row.getAttribute("data-key")))
  })
  root.querySelectorAll(".bng-earth-effort-btn").forEach(btn => {
    btn.addEventListener("click", () => setEffort(btn.getAttribute("data-effort")))
  })
  root.querySelector("#bng-earth-addons-refresh").addEventListener("click", triggerRefresh)
  root.querySelector("#bng-earth-addons-bench").addEventListener("click", startBenchmark)
  root.querySelector("#bng-earth-bench-folder").addEventListener("click", openBenchFolder)
  root.querySelector("#bng-earth-bench-issue").addEventListener("click", openBenchIssue)

  updateDOM()
}

export function updateDOM() {
  const root = document.getElementById(ROOT_ID)
  if (!root) return
  const st = getState()
  if (!st.visible) {
    root.style.display = "none"
    return
  }
  root.style.display = "block"
  const pill = root.querySelector("#bng-earth-addons-pill-view")
  const card = root.querySelector("#bng-earth-addons-card-view")
  if (st.minimized) {
    pill.style.display = "inline-flex"
    card.style.display = "none"
    const pillText = root.querySelector("#bng-earth-addons-pill-text")
    if (pillText) pillText.textContent = `Generation Addons (${st.addonProvence ? "ON" : "OFF"})`
    return
  }
  pill.style.display = "none"
  card.style.display = "block"

  ;["addonProvence", "sourceIgnRpg", "sourceIgnOrtho", "sourceProvenceBiomes"].forEach(k => {
    const sw = root.querySelector(`[data-switch="${k}"]`)
    if (sw) sw.classList.toggle("on", !!st[k])
  })
  const sub = root.querySelector("#bng-earth-addons-subrows")
  if (sub) sub.style.display = st.addonProvence ? "block" : "none"

  root.querySelectorAll(".bng-earth-effort-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-effort") === st.effortProfile)
  })
  const benchBtn = root.querySelector("#bng-earth-addons-bench")
  if (benchBtn) {
    benchBtn.classList.toggle("running", !!st.benchRunning)
    benchBtn.textContent = st.benchRunning
      ? `Recording ${st.benchElapsed}/${st.benchDuration}s`
      : "Benchmark (30s)"
  }
  const resBox = root.querySelector("#bng-earth-bench-result")
  const resSum = root.querySelector("#bng-earth-bench-summary")
  if (resBox && resSum) {
    if (!st.benchRunning && st.benchSummary) {
      resBox.style.display = "block"
      resSum.textContent = `Last Benchmark: ${st.benchSummary}`
    } else {
      resBox.style.display = "none"
    }
  }
  const noteEl = root.querySelector("#bng-earth-addons-note")
  if (noteEl) {
    noteEl.textContent = st.note || ""
    noteEl.style.display = st.note ? "block" : "none"
  }
}

export function open() {
  const st = getState()
  st.visible = true
  st.minimized = false
  if (!document.getElementById(ROOT_ID)) buildDOMOnce()
  syncFromLua()
  pollBenchStatus()
  updateDOM()
}

export function close() {
  const st = getState()
  st.visible = false
  updateDOM()
}

export function toggle() {
  const st = getState()
  st.visible = !st.visible
  if (st.visible) {
    st.minimized = false
    syncFromLua()
    pollBenchStatus()
  }
  updateDOM()
}

export function start() {
  stop()
  window.bngEarthAddonsWindow = { open, close, toggle, updateDOM, syncFromLua, stop }
  buildDOMOnce()
  syncFromLua()
  pollBenchStatus()
}

export function stop() {
  const st = getState()
  if (st.benchPollTimer) {
    clearInterval(st.benchPollTimer)
    st.benchPollTimer = null
  }
  const root = document.getElementById(ROOT_ID)
  if (root) root.remove()
}
