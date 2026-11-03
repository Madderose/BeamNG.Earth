// Standalone floating "Generation Addons" window in the CEF UI layer (works in DX12/Vulkan both in gameplay and menus).

const ROOT_ID = "bng-earth-addons-floating-root"
const STYLE_ID = "bng-earth-addons-floating-style"

let state = {
  open: true,
  addonProvence: true,
  sourceIgnRpg: true,
  sourceIgnOrtho: true,
  sourceProvenceBiomes: true,
  effortProfile: "balanced",
  note: "",
  posX: 28,
  posY: 84,
}

let pollId = null

const EFFORT_PROFILES = [
  { id: "low", label: "Low" },
  { id: "balanced", label: "Balanced" },
  { id: "high", label: "High" },
  { id: "ultra", label: "Ultra" },
  { id: "auto_fps", label: "Auto-FPS" },
]

function engineLua(code, cb) {
  if (window.bngApi && window.bngApi.engineLua) {
    window.bngApi.engineLua(code, cb)
  }
}

function injectStyles() {
  if (document.getElementById(STYLE_ID)) return
  const style = document.createElement("style")
  style.id = STYLE_ID
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
      width: 360px;
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
    .bng-earth-addons-minbtn {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.16);
      color: #ddd;
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 12px;
      cursor: pointer;
    }
    .bng-earth-addons-minbtn:hover {
      background: rgba(255, 102, 0, 0.25);
      border-color: #ff6600;
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
    .bng-earth-refresh-btn {
      width: 100%;
      background: rgba(255, 102, 0, 0.18);
      border: 1px solid #ff6600;
      color: #ffffff;
      border-radius: 5px;
      padding: 7px 10px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
    }
    .bng-earth-refresh-btn:hover {
      background: #ff6600;
    }
    .bng-earth-addons-note {
      font-size: 11.5px;
      color: #ff9944;
      text-align: center;
      margin-top: 6px;
    }
  `
  document.head.appendChild(style)
}

function syncFromLua() {
  engineLua("beamngEarth_settings and beamngEarth_settings.getAll() or nil", res => {
    if (!res) return
    state.addonProvence = res.addonProvence !== false
    state.sourceIgnRpg = res.sourceIgnRpg !== false
    state.sourceIgnOrtho = res.sourceIgnOrtho !== false
    state.sourceProvenceBiomes = res.sourceProvenceBiomes !== false
    state.effortProfile = res.effortProfile || "balanced"
    render()
  })
}

function toggleBool(key) {
  state[key] = !state[key]
  state.note = "Applying & refreshing world..."
  render()
  engineLua(`beamngEarth_settings and beamngEarth_settings.uiSet(${JSON.stringify(key)}, ${state[key] ? "true" : "false"}) or nil`, () => {
    state.note = "Updated"
    render()
    setTimeout(() => { if (state.note === "Updated") { state.note = ""; render() } }, 2500)
  })
}

function setEffort(id) {
  state.effortProfile = id
  state.note = `Effort profile: ${id}...`
  render()
  engineLua(`beamngEarth_settings and beamngEarth_settings.uiSet("effortProfile", ${JSON.stringify(id)}) or nil`, () => {
    state.note = `Effort: ${id}`
    render()
    setTimeout(() => { if (state.note.startsWith("Effort:")) { state.note = ""; render() } }, 2500)
  })
}

function triggerRefresh() {
  state.note = "Refreshing nearby vegetation & buildings..."
  render()
  engineLua("beamngEarth_settings and beamngEarth_settings.uiRefreshWorld() or nil", () => {
    state.note = "World refresh triggered"
    render()
    setTimeout(() => { if (state.note === "World refresh triggered") { state.note = ""; render() } }, 3000)
  })
}

function ensureRoot() {
  injectStyles()
  let root = document.getElementById(ROOT_ID)
  if (!root) {
    root = document.createElement("div")
    root.id = ROOT_ID
    document.body.appendChild(root)
  }
  root.style.left = `${state.posX}px`
  root.style.top = `${state.posY}px`
  return root
}

function attachDrag(headerEl, rootEl) {
  let dragging = false
  let startX = 0, startY = 0, origX = 0, origY = 0
  headerEl.addEventListener("mousedown", e => {
    if (e.target.tagName === "BUTTON") return
    dragging = true
    startX = e.clientX
    startY = e.clientY
    origX = state.posX
    origY = state.posY
    const onMove = ev => {
      if (!dragging) return
      state.posX = Math.max(8, Math.min(window.innerWidth - 370, origX + (ev.clientX - startX)))
      state.posY = Math.max(8, Math.min(window.innerHeight - 120, origY + (ev.clientY - startY)))
      rootEl.style.left = `${state.posX}px`
      rootEl.style.top = `${state.posY}px`
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

export function render() {
  const root = ensureRoot()
  if (!state.open) {
    root.innerHTML = `
      <div class="bng-earth-addons-pill" id="bng-earth-addons-expand">
        <span class="bng-earth-addons-slash"></span>
        <span>Generation Addons (${state.addonProvence ? "ON" : "OFF"})</span>
      </div>
    `
    const btn = root.querySelector("#bng-earth-addons-expand")
    if (btn) btn.addEventListener("click", () => { state.open = true; syncFromLua(); render() })
    return
  }

  const subRows = state.addonProvence ? `
    <div class="bng-earth-addons-row sub" data-key="sourceIgnRpg">
      <span>- IGN BD TOPO & RPG Parcels</span>
      <div class="bng-earth-switch ${state.sourceIgnRpg ? "on" : ""}"></div>
    </div>
    <div class="bng-earth-addons-row sub" data-key="sourceIgnOrtho">
      <span>- IGN 20 cm Orthophoto Roof Tinting</span>
      <div class="bng-earth-switch ${state.sourceIgnOrtho ? "on" : ""}"></div>
    </div>
    <div class="bng-earth-addons-row sub" data-key="sourceProvenceBiomes">
      <span>- Provence Crops & Biomes</span>
      <div class="bng-earth-switch ${state.sourceProvenceBiomes ? "on" : ""}"></div>
    </div>
  ` : ""

  const effortBtns = EFFORT_PROFILES.map(p => `
    <button class="bng-earth-effort-btn ${state.effortProfile === p.id ? "active" : ""}" data-effort="${p.id}">${p.label}</button>
  `).join("")

  root.innerHTML = `
    <div class="bng-earth-addons-card">
      <div class="bng-earth-addons-header" id="bng-earth-addons-drag">
        <div class="bng-earth-addons-title">
          <span class="bng-earth-addons-slash"></span>
          <span>Generation Addons</span>
        </div>
        <button class="bng-earth-addons-minbtn" id="bng-earth-addons-min" title="Minimize to pill">Hide</button>
      </div>
      <div class="bng-earth-addons-row" data-key="addonProvence">
        <span>France & Provence Ground Truth Pack</span>
        <div class="bng-earth-switch ${state.addonProvence ? "on" : ""}"></div>
      </div>
      ${subRows}
      <div class="bng-earth-effort-box">
        <div class="bng-earth-effort-label">Ground-Truth Effort Profile (Layer B)</div>
        <div class="bng-earth-effort-pills">${effortBtns}</div>
      </div>
      <button class="bng-earth-refresh-btn" id="bng-earth-addons-refresh">Refresh World Around You</button>
      ${state.note ? `<div class="bng-earth-addons-note">${state.note}</div>` : ""}
    </div>
  `

  const header = root.querySelector("#bng-earth-addons-drag")
  if (header) attachDrag(header, root)

  const minBtn = root.querySelector("#bng-earth-addons-min")
  if (minBtn) minBtn.addEventListener("click", () => { state.open = false; render() })

  root.querySelectorAll(".bng-earth-addons-row").forEach(row => {
    row.addEventListener("click", () => toggleBool(row.getAttribute("data-key")))
  })

  root.querySelectorAll(".bng-earth-effort-btn").forEach(btn => {
    btn.addEventListener("click", () => setEffort(btn.getAttribute("data-effort")))
  })

  const refBtn = root.querySelector("#bng-earth-addons-refresh")
  if (refBtn) refBtn.addEventListener("click", triggerRefresh)
}

export function open() {
  state.open = true
  syncFromLua()
  render()
}

export function close() {
  state.open = false
  render()
}

export function toggle() {
  state.open = !state.open
  if (state.open) syncFromLua()
  render()
}

export function start() {
  window.bngEarthAddonsWindow = { open, close, toggle, render, syncFromLua }
  syncFromLua()
  render()
  if (pollId) clearInterval(pollId)
  pollId = setInterval(syncFromLua, 3000)
}

export function stop() {
  if (pollId) clearInterval(pollId)
  pollId = null
  const root = document.getElementById(ROOT_ID)
  if (root) root.remove()
}
