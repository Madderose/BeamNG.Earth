# Agent Instructions & Guidelines

## Architecture & Coding Standards
- Follow established BeamNG.Earth conventions for L-level terrain, procedural roads, vegetation, and buildings.
- Maintain high-speed streaming stability and strict frame budgets (<16ms).
- Always validate changes with the parallel test runner: `python tools/parallel_tests.py -j 12`.

## In-Engine Performance Diagnostics & Telemetry Capture
- **BeamNG MCP Port Discovery**:
  - The built-in BeamNG MCP server binds to `http://127.0.0.1:29292/mcp` or `http://127.0.0.1:29293/mcp`.
  - Always use `tools/mcp.py` or probe candidates `[29292, 29293, 29294]` rather than assuming port 29292.
- **UI State & Debug Overlay Visibility**:
  - Debug graphs and metrics overlays are suppressed when the game UI is on the pause/ESC menu (`pause.system`).
  - Always ensure the UI is in play mode: `set_ui_state({"route": "play"})` and verify `get_simulation_state` shows `timeScale > 0`.
- **In-Engine Performance Display Controls**:
  - **Performance Graph**: Toggle via MCP `trigger_action({"action": "toggle_performance_graph"})` or GE Lua `togglePerformanceGraph()` (bound to `Ctrl+Shift+F`).
  - **Performance Metrics Overlay**: Toggle via MCP `trigger_action({"action": "cycle_metrics"})` or GE Lua `extensions.core_metrics.toggle()` (bound to `Ctrl+F`).
  - **GPU Timings Overlay**: Enable in GE Lua with `Engine.Debug.setGpuTimingOverlayVisible(true)`.
  - **Optick Profiler**: Trigger via MCP `profiler_run({"duration": 10})` or launch GUI via `run_optick_ui()` (bound to `Ctrl+Alt+O`).
- **Automated Performance Capture & Reporting**:
  - Run `python tools/perf_capture.py [options]` to record live frame latencies, subsystem breakdowns (Render, Lua, Physics, Shadows), VRAM, and streaming engine metrics.
  - Generates executive markdown reports in `perf_reports/perf_report_<timestamp>.md` and raw telemetry in `perf_reports/perf_data_<timestamp>.json`.
  - Validate that p95 frame latency remains `<16.67ms` and 60+ FPS compliance is `≥95%`.

## Versioning, Building, and Publishing Releases
- **Always check current named version before building and publishing**:
  - Read `VERSION` in the workspace root.
  - Run `git fetch origin --tags; git fetch upstream --tags`.
  - Check existing releases: `gh release list --repo Madderose/BeamNG.Earth`.
  - Check upstream latest commits and tags (`upstream/main`).
- **Avoid Name Mistakes & CI/CD Collisions**:
  - Never attempt to create or publish a release using an existing tag/release name.
  - Be aware that pushing to `main` triggers `.github/workflows/release.yml`. Never publish a release via CLI under the same version while pushing to `main` at the same time to avoid race condition conflicts (`a release with the same tag name already exists`).
  - Use appropriate semantic versions and prerelease markers (`preview`, `alpha`, `beta`, `rc`, `experimental`).
- **Remotes**:
  - `origin`: personal fork (`Madderose/BeamNG.Earth`).
  - `upstream`: original repository (`TecnaGamer/BeamNG.Earth`).
