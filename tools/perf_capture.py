#!/usr/bin/env python3
"""BeamNG.Earth Performance Capture & Reporting Tool.

Connects to BeamNG's built-in MCP server, samples real-time frame telemetry,
subsystem timings, streaming engine status, and VRAM over a designated duration,
then generates an executive markdown performance report and raw JSON data.

Usage:
  python tools/perf_capture.py [options]

Examples:
  python tools/perf_capture.py --duration 10
  python tools/perf_capture.py --duration 15 --toggle-graph --unpause
  python tools/perf_capture.py --duration 30 --interval 0.25 --out perf_reports/high_speed_drive.md
"""

import argparse
import datetime
import json
import math
import os
import sys
import time

# Ensure local tools can be imported
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import mcp  # noqa: E402


def ensure_play_state():
    """Ensure game UI is back to play and unpaused."""
    try:
        mcp.call("set_ui_state", {"route": "play"})
        # Best effort unpause physics
        mcp.call("resume_physics")
        mcp.call("run_lua", {"code": "if simTimeAuthority and simTimeAuthority.unpause then simTimeAuthority.unpause() end"})
    except Exception as e:
        print(f"[Warning] Failed to ensure play state: {e}", file=sys.stderr)


def toggle_perf_graph():
    """Ensure native performance graph is toggled."""
    try:
        mcp.call("trigger_action", {"action": "toggle_performance_graph"})
    except Exception as e:
        # Fallback to direct GE Lua call
        try:
            mcp.call("run_lua", {"code": "togglePerformanceGraph()"})
        except Exception:
            print(f"[Warning] Failed to toggle performance graph: {e}", file=sys.stderr)


def enable_metrics_overlay():
    """Ensure core_metrics is loaded and GPU timing overlay is visible."""
    code = """
    extensions.load('core_metrics')
    if core_metrics and core_metrics.currentMode == 0 then
        core_metrics.toggle()
    end
    if Engine.Debug and Engine.Debug.setGpuTimingOverlayVisible then
        Engine.Debug.setGpuTimingOverlayVisible(true)
    end
    """
    try:
        mcp.call("run_lua", {"code": code})
    except Exception as e:
        print(f"[Warning] Failed to enable metrics overlay: {e}", file=sys.stderr)


def query_sample():
    """Query a single frame sample of telemetry from BeamNG MCP."""
    sample = {
        "timestamp": time.time(),
        "metrics": {},
        "console_vars": {},
        "vram": None,
        "streaming": {},
        "speed_mph": 0.0,
    }

    # 1. Subsystem metrics from Engine.Debug
    try:
        raw_m = mcp.call("get_performance_metrics")
        sample["metrics"] = json.loads(raw_m)
    except Exception:
        pass

    # 2. Console FPS & timing variables
    lua_vars = """
    local v = {}
    local names = {
        "fps::instantaneous", "fps::avg", "fps::p90", "fps::p95", "fps::p99",
        "fps::min", "fps::max", "fps::waitForGPU", "fps::cpuTime", "fps::gpuTime"
    }
    for _, n in ipairs(names) do
        local val = VariableRegistry.get("$"..n, nil)
        if val then v[n] = tonumber(val) end
    end
    return jsonEncode(v)
    """
    try:
        raw_cv = mcp.call("run_lua", {"code": lua_vars})
        sample["console_vars"] = json.loads(raw_cv)
    except Exception:
        pass

    # 3. GPU VRAM
    try:
        raw_vram = mcp.call("get_vram_usage")
        sample["vram"] = json.loads(raw_vram) if raw_vram.startswith("{") else raw_vram.strip()
    except Exception:
        pass

    # 4. Companion streaming & vehicle speed
    lua_core = """
    local s = beamngEarth_core and beamngEarth_core.status and beamngEarth_core.status()
    local v = getPlayerVehicle(0)
    local vel = v and v:getVelocity()
    local speed = vel and (vel:length() * 2.23694) or 0
    local dmg = (v and map and map.objects and map.objects[v:getId()] and map.objects[v:getId()].damage) or 0
    return jsonEncode({status = s, speed_mph = speed, damage = dmg})
    """
    try:
        raw_core = mcp.call("run_lua", {"code": lua_core})
        d_core = json.loads(raw_core)
        sample["speed_mph"] = d_core.get("speed_mph", 0.0)
        sample["damage"] = d_core.get("damage", 0.0)
        # Parse core status table if present
        st_text = d_core.get("status")
        if st_text:
            sample["streaming_raw"] = st_text
    except Exception:
        pass

    return sample


def calculate_stats(samples):
    """Compute comprehensive performance statistics from recorded samples."""
    fps_list = []
    cpu_ms_list = []
    gpu_ms_list = []
    render_ms_list = []
    lua_ms_list = []
    phys_ms_list = []
    shadow_ms_list = []
    wait_gpu_ms_list = []
    speeds = []
    hitches = []  # Frame times > 33.3ms (drops below 30 fps)

    for s in samples:
        cv = s.get("console_vars", {})
        m = s.get("metrics", {})

        inst_fps = cv.get("fps::instantaneous")
        if inst_fps and inst_fps > 0:
            fps_list.append(inst_fps)
            frame_ms = 1000.0 / inst_fps
            if frame_ms > 33.33:
                hitches.append({
                    "timestamp": s["timestamp"],
                    "frame_ms": frame_ms,
                    "fps": inst_fps,
                    "render_ms": m.get("Render", 0.0),
                    "lua_ms": m.get("Lua", 0.0),
                    "physics_ms": m.get("PhysicsAndVLUA", 0.0) + m.get("PhysicsNodes", 0.0),
                    "wait_gpu_ms": cv.get("fps::waitForGPU", 0.0),
                    "speed_mph": s.get("speed_mph", 0.0),
                })

        if "fps::cpuTime" in cv and cv["fps::cpuTime"] is not None:
            cpu_ms_list.append(cv["fps::cpuTime"])
        if "fps::gpuTime" in cv and cv["fps::gpuTime"] is not None and cv["fps::gpuTime"] >= 0:
            gpu_ms_list.append(cv["fps::gpuTime"])
        if "fps::waitForGPU" in cv and cv["fps::waitForGPU"] is not None:
            wait_gpu_ms_list.append(cv["fps::waitForGPU"])

        if "Render" in m:
            render_ms_list.append(m["Render"])
        if "Lua" in m:
            lua_ms_list.append(m["Lua"])
        p_total = m.get("PhysicsAndVLUA", 0.0) + m.get("PhysicsNodes", 0.0)
        if p_total > 0:
            phys_ms_list.append(p_total)
        if "RenderShadows" in m:
            shadow_ms_list.append(m["RenderShadows"])

        speeds.append(s.get("speed_mph", 0.0))

    def percentile(arr, p):
        if not arr:
            return 0.0
        sorted_arr = sorted(arr)
        k = (len(sorted_arr) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_arr[int(k)]
        d0 = sorted_arr[int(f)] * (c - k)
        d1 = sorted_arr[int(c)] * (k - f)
        return d0 + d1

    def mean(arr):
        return sum(arr) / max(1, len(arr))

    frame_ms_list = [1000.0 / f for f in fps_list] if fps_list else []

    stats = {
        "sample_count": len(samples),
        "fps": {
            "mean": mean(fps_list),
            "median": percentile(fps_list, 50),
            "min": min(fps_list) if fps_list else 0.0,
            "max": max(fps_list) if fps_list else 0.0,
            "p1_low": percentile(fps_list, 1),
            "p5_low": percentile(fps_list, 5),
        },
        "frame_ms": {
            "mean": mean(frame_ms_list),
            "median": percentile(frame_ms_list, 50),
            "min": min(frame_ms_list) if frame_ms_list else 0.0,
            "max": max(frame_ms_list) if frame_ms_list else 0.0,
            "p90": percentile(frame_ms_list, 90),
            "p95": percentile(frame_ms_list, 95),
            "p99": percentile(frame_ms_list, 99),
        },
        "subsystems": {
            "render_ms": {"mean": mean(render_ms_list), "max": max(render_ms_list) if render_ms_list else 0.0},
            "lua_ms": {"mean": mean(lua_ms_list), "max": max(lua_ms_list) if lua_ms_list else 0.0},
            "physics_ms": {"mean": mean(phys_ms_list), "max": max(phys_ms_list) if phys_ms_list else 0.0},
            "shadow_ms": {"mean": mean(shadow_ms_list), "max": max(shadow_ms_list) if shadow_ms_list else 0.0},
            "cpu_ms": {"mean": mean(cpu_ms_list), "max": max(cpu_ms_list) if cpu_ms_list else 0.0},
            "gpu_ms": {"mean": mean(gpu_ms_list), "max": max(gpu_ms_list) if gpu_ms_list else 0.0},
            "wait_gpu_ms": {"mean": mean(wait_gpu_ms_list), "max": max(wait_gpu_ms_list) if wait_gpu_ms_list else 0.0},
        },
        "budget": {
            "under_16ms_pct": (sum(1 for m in frame_ms_list if m <= 16.67) / max(1, len(frame_ms_list))) * 100.0,
            "under_33ms_pct": (sum(1 for m in frame_ms_list if m <= 33.33) / max(1, len(frame_ms_list))) * 100.0,
            "hitch_count": len(hitches),
        },
        "hitches": hitches,
        "speed": {
            "mean_mph": mean(speeds),
            "max_mph": max(speeds) if speeds else 0.0,
        },
    }
    return stats


def generate_markdown_report(stats, duration, screenshot_path=None, meta=None):
    """Format performance statistics into an executive markdown document."""
    b = stats["budget"]
    fps = stats["fps"]
    fms = stats["frame_ms"]
    sub = stats["subsystems"]

    # Evaluation verdict
    passed = fms["p95"] <= 16.67 and b["under_16ms_pct"] >= 95.0
    status_badge = "✅ PASS" if passed else ("⚠️ ACCEPTABLE" if b["under_33ms_pct"] >= 95.0 else "❌ REGRESSION")

    lines = [
        f"# BeamNG.Earth Performance Report",
        f"",
        f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Duration:** {duration:.1f} seconds ({stats['sample_count']} samples)  ",
        f"**Status:** {status_badge}  ",
        f"",
        f"---",
        f"",
        f"## 1. Executive Summary",
        f"",
        f"| Metric | Target | Measured | Result |",
        f"| :--- | :--- | :--- | :--- |",
        f"| **Average Framerate** | ≥ 60.0 FPS | **{fps['mean']:.1f} FPS** | {'✅' if fps['mean'] >= 60.0 else '⚠️'} |",
        f"| **Median Framerate** | ≥ 60.0 FPS | **{fps['median']:.1f} FPS** | {'✅' if fps['median'] >= 60.0 else '⚠️'} |",
        f"| **1% Low Framerate** | ≥ 45.0 FPS | **{fps['p1_low']:.1f} FPS** | {'✅' if fps['p1_low'] >= 45.0 else '⚠️'} |",
        f"| **Mean Frame Time** | < 16.67 ms | **{fms['mean']:.2f} ms** | {'✅' if fms['mean'] <= 16.67 else '❌'} |",
        f"| **p95 Frame Latency** | < 16.67 ms | **{fms['p95']:.2f} ms** | {'✅' if fms['p95'] <= 16.67 else '❌'} |",
        f"| **p99 Frame Latency** | < 25.00 ms | **{fms['p99']:.2f} ms** | {'✅' if fms['p99'] <= 25.00 else '⚠️'} |",
        f"| **Max Hitch Frame** | < 50.00 ms | **{fms['max']:.2f} ms** | {'✅' if fms['max'] < 50.00 else '❌'} |",
        f"| **Frames within 16.6ms** | ≥ 95.0% | **{b['under_16ms_pct']:.1f}%** | {'✅' if b['under_16ms_pct'] >= 95.0 else '⚠️'} |",
        f"",
        f"---",
        f"",
        f"## 2. Subsystem Latency Breakdown",
        f"",
        f"| Engine Subsystem | Mean Latency (ms) | Peak Latency (ms) | % of Frame Budget |",
        f"| :--- | :--- | :--- | :--- |",
        f"| **Render Core** | {sub['render_ms']['mean']:.2f} ms | {sub['render_ms']['max']:.2f} ms | {sub['render_ms']['mean']/16.67*100.0:.1f}% |",
        f"| **Shadow Passes** | {sub['shadow_ms']['mean']:.2f} ms | {sub['shadow_ms']['max']:.2f} ms | {sub['shadow_ms']['mean']/16.67*100.0:.1f}% |",
        f"| **Game Engine Lua VM** | {sub['lua_ms']['mean']:.2f} ms | {sub['lua_ms']['max']:.2f} ms | {sub['lua_ms']['mean']/16.67*100.0:.1f}% |",
        f"| **Physics Core & VLUA** | {sub['physics_ms']['mean']:.2f} ms | {sub['physics_ms']['max']:.2f} ms | {sub['physics_ms']['mean']/16.67*100.0:.1f}% |",
        f"| **Wait for GPU** | {sub['wait_gpu_ms']['mean']:.2f} ms | {sub['wait_gpu_ms']['max']:.2f} ms | - |",
        f"",
        f"---",
        f"",
        f"## 3. Hitches & Drops Analysis",
        f"",
    ]

    hitches = stats["hitches"]
    if not hitches:
        lines.append("> [!TIP]\n> **Zero frame hitches recorded!** Frame times remained strictly within smooth operational margins throughout the entire test.")
    else:
        lines.append(f"> [!WARNING]\n> **{len(hitches)} frame drop(s)** exceeded the 33.3ms threshold (>30 FPS drops):")
        lines.append("")
        lines.append("| Sample Time | Frame Time | Inst FPS | Render | Lua | Physics | GPU Wait | Vehicle Speed |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for h in hitches[:15]:
            t_rel = h["timestamp"] - hitches[0]["timestamp"] if hitches else 0
            lines.append(f"| +{t_rel:.2f}s | **{h['frame_ms']:.1f} ms** | {h['fps']:.1f} | {h['render_ms']:.1f} ms | {h['lua_ms']:.1f} ms | {h['physics_ms']:.1f} ms | {h['wait_gpu_ms']:.1f} ms | {h['speed_mph']:.1f} mph |")
        if len(hitches) > 15:
            lines.append(f"| ... | *({len(hitches) - 15} additional hitches truncated)* | | | | | | |")

    lines += [
        f"",
        f"---",
        f"",
        f"## 4. Vehicle & Streaming Context",
        f"",
        f"- **Average Speed:** {stats['speed']['mean_mph']:.1f} mph (Peak: {stats['speed']['max_mph']:.1f} mph)",
    ]

    if meta:
        for k, v in meta.items():
            lines.append(f"- **{k}:** {v}")

    if screenshot_path and os.path.exists(screenshot_path):
        lines += [
            f"",
            f"---",
            f"",
            f"## 5. In-Engine Capture",
            f"",
            f"![Performance Capture Screenshot]({screenshot_path.replace(os.sep, '/')})",
        ]

    lines.append("")
    return "\n".join(lines)


def capture_performance(duration=10.0, interval=0.5, out_md=None, out_json=None,
                        toggle_graph=False, toggle_metrics=False, unpause=True,
                        screenshot=True, optick=False):
    """Main program entry to capture performance telemetry and write reports."""
    print(f"[PerfCapture] Initializing BeamNG performance session...")
    print(f"[PerfCapture] Active MCP endpoint: {mcp.get_mcp_url()}")

    if unpause:
        ensure_play_state()

    if toggle_graph:
        toggle_perf_graph()

    if toggle_metrics:
        enable_metrics_overlay()

    if optick:
        try:
            mcp.call("profiler_run", {"duration": duration})
            print(f"[PerfCapture] Optick capture initiated ({duration:.1f}s)")
        except Exception as e:
            print(f"[PerfCapture] Optick profiler not available: {e}")

    samples = []
    start_time = time.time()
    next_sample = start_time
    screenshot_taken = None

    print(f"[PerfCapture] Sampling telemetry for {duration:.1f}s at {interval:.2f}s intervals...")

    # Midpoint trigger for screenshot if requested
    screenshot_due = start_time + (duration / 2.0)

    while True:
        now = time.time()
        elapsed = now - start_time
        if elapsed >= duration:
            break

        # Check for screenshot at midpoint
        if screenshot and not screenshot_taken and now >= screenshot_due:
            try:
                res = mcp.call("screenshot")
                if res and os.path.exists(res):
                    screenshot_taken = res
            except Exception:
                pass

        if now >= next_sample:
            s = query_sample()
            samples.append(s)
            next_sample = now + interval

        time.sleep(0.05)

    print(f"[PerfCapture] Completed recording {len(samples)} samples.")

    # Calculate statistics
    stats = calculate_stats(samples)

    # Determine paths
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = os.path.join(os.getcwd(), "perf_reports")
    os.makedirs(reports_dir, exist_ok=True)

    if not out_md:
        out_md = os.path.join(reports_dir, f"perf_report_{timestamp}.md")
    if not out_json:
        out_json = os.path.join(reports_dir, f"perf_data_{timestamp}.json")

    # Save JSON raw data
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "samples": samples}, f, indent=2)
    print(f"[PerfCapture] Raw telemetry saved: {out_json}")

    # Generate and save Markdown report
    md_content = generate_markdown_report(stats, duration, screenshot_path=screenshot_taken)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[PerfCapture] Performance report saved: {out_md}")

    # Print summary to stdout
    fps = stats["fps"]
    fms = stats["frame_ms"]
    print("\n" + "=" * 60)
    print("           BEAMNG.EARTH PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f" Average FPS        : {fps['mean']:.1f} FPS (Median: {fps['median']:.1f} FPS)")
    print(f" 1% Low FPS         : {fps['p1_low']:.1f} FPS (Min: {fps['min']:.1f} FPS)")
    print(f" Frame Latency Mean : {fms['mean']:.2f} ms")
    print(f" Frame Latency p95  : {fms['p95']:.2f} ms")
    print(f" Frame Latency p99  : {fms['p99']:.2f} ms")
    print(f" Max Hitch Latency  : {fms['max']:.2f} ms")
    print(f" Frames < 16.67ms   : {stats['budget']['under_16ms_pct']:.1f}%")
    print(f" Drops > 33.33ms    : {stats['budget']['hitch_count']} frames")
    print("=" * 60)

    return out_md, out_json, stats


def main():
    parser = argparse.ArgumentParser(description="Capture BeamNG.Earth performance telemetry and generate report")
    parser.add_argument("--duration", type=float, default=10.0, help="Capture duration in seconds (default: 10.0)")
    parser.add_argument("--interval", type=float, default=0.5, help="Sampling interval in seconds (default: 0.5)")
    parser.add_argument("--out", type=str, default=None, help="Output markdown report path")
    parser.add_argument("--json-out", type=str, default=None, help="Output raw JSON data path")
    parser.add_argument("--toggle-graph", action="store_true", help="Toggle native performance graph on")
    parser.add_argument("--toggle-metrics", action="store_true", help="Toggle core_metrics overlay on")
    parser.add_argument("--no-unpause", action="store_true", help="Do not force play/unpause state")
    parser.add_argument("--no-screenshot", action="store_true", help="Do not capture midpoint screenshot")
    parser.add_argument("--optick", action="store_true", help="Trigger concurrent Optick profiler capture")

    args = parser.parse_args()

    capture_performance(
        duration=args.duration,
        interval=args.interval,
        out_md=args.out,
        out_json=args.json_out,
        toggle_graph=args.toggle_graph,
        toggle_metrics=args.toggle_metrics,
        unpause=not args.no_unpause,
        screenshot=not args.no_screenshot,
        optick=args.optick,
    )


if __name__ == "__main__":
    main()
