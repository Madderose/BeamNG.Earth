"""
BeamNG.Earth Phase 10 orchestrator: RenderShadows stutter — proposal round.

Launches 4 parallel AGY Argon 4 Medium sub-agents (gemini-4-argon-medium), each producing a proposal.md
plus ready-to-apply .diff files in runs/optimization_logs/phase10/<task>/ (proposal only, no source edits).
Updates the Phase 10 table in task_tracker.md every 60 s (row status) and appends a compact heartbeat
every 5 min. Kills a worker after TIMEOUT_S.

Usage:  python tools/orchestrate_phase10.py [--only TASK-P10-A,TASK-P10-C]
        python tools/orchestrate_phase10.py --wave 1     (Wave 1 implementation round: workers edit their
                                                          owned files in place and write report.md)
"""

import argparse
import datetime
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKER_PATH = os.path.join(REPO_ROOT, "task_tracker.md")
OUT_ROOT = os.path.join(REPO_ROOT, "runs", "optimization_logs", "phase10")
AGY_EXE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "agy", "bin", "agy.exe")
if not os.path.exists(AGY_EXE):
    AGY_EXE = "agy"

MODEL = "gemini-4-argon-medium"
TIMEOUT_S = 50 * 60
ROW_EVERY_S = 60
HEARTBEAT_EVERY_S = 300

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

TASKS = [
    {"id": "TASK-P10-A", "name": "Engine shadow API discovery & dead-toggle replacement",
     "prompt": "subagent_task_p10a_engine_api.txt", "dir": "p10a_engine_api"},
    {"id": "TASK-P10-B", "name": "Streaming-burst shadow spike amortization",
     "prompt": "subagent_task_p10b_spike_amortization.txt", "dir": "p10b_spike_amortization"},
    {"id": "TASK-P10-C", "name": "Shadow caster reduction via materials & server meshes",
     "prompt": "subagent_task_p10c_material_casters.txt", "dir": "p10c_material_casters"},
    {"id": "TASK-P10-D", "name": "Scene-graph object count & Forest consolidation",
     "prompt": "subagent_task_p10d_scenegraph_forests.txt", "dir": "p10d_scenegraph_forests"},
]

# Wave 1 implementation round (user-approved): disjoint file ownership, see scratch/phase10w1_shared_briefing.md
TASKS_W1 = [
    {"id": "TASK-P10W1-GOV", "name": "Governor R1 fix (urgent beats burst), transient burst",
     "prompt": "subagent_task_p10w1_governor.txt", "dir": os.path.join("wave1", "w1_governor")},
    {"id": "TASK-P10W1-SHADOW", "name": "shadowctl slim-down + anti-pumping burst profile",
     "prompt": "subagent_task_p10w1_shadowctl.txt", "dir": os.path.join("wave1", "w2_shadowctl")},
    {"id": "TASK-P10W1-TREES", "name": "trees: drop super-tiles, Forest cap rebase, shadowNullDetailSize",
     "prompt": "subagent_task_p10w1_trees.txt", "dir": os.path.join("wave1", "w3_trees")},
    {"id": "TASK-P10W1-ROADS", "name": "roads/farfield/materials/server: Wave-2 removal + tests",
     "prompt": "subagent_task_p10w1_roads.txt", "dir": os.path.join("wave1", "w4_roads")},
]
DELIVERABLE = "proposal.md"


def now(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now().strftime(fmt)


def _rw_tracker(fn):
    try:
        with open(TRACKER_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        content = fn(content)
        with open(TRACKER_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    except Exception as e:  # never let tracker I/O kill the orchestration
        print(f"Warning: tracker update failed: {e}", flush=True)


def set_row_status(task_id, status, log=True):
    """Rewrite the 'Execution Status' cell (last column) of the task's Phase 10 table row."""
    def fn(content):
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("|") and f"**{task_id}**" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    parts[-2] = f" **{status}** "
                    lines[i] = "|".join(parts)
                break
        if log:
            lines.append(f"> `[{now()}]` **{task_id}**: {status}")
        return "\n".join(lines)
    _rw_tracker(fn)


def append_tracker(text):
    _rw_tracker(lambda c: c.rstrip("\n") + "\n" + text + "\n")


def last_status(log_file):
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return "starting"
    for line in reversed(lines):
        if "STATUS_UPDATE:" in line:
            return line[line.index("STATUS_UPDATE:") + len("STATUS_UPDATE:"):].strip()[:90]
    return f"running ({len(lines)} log lines)"


def launch(task):
    out_dir = os.path.join(OUT_ROOT, task["dir"])
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(REPO_ROOT, "scratch", task["prompt"]), "r", encoding="utf-8") as f:
        prompt = f.read()
    log_path = os.path.join(out_dir, "agent.log")
    lf = open(log_path, "w", encoding="utf-8")
    cmd = [AGY_EXE, "--model", MODEL, "--effort", "medium", "--dangerously-skip-permissions", "-p", prompt]
    proc = subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=lf, stderr=subprocess.STDOUT)
    print(f"[{now('%H:%M:%S')}] Launched {task['id']} -> PID {proc.pid}", flush=True)
    set_row_status(task["id"], f"RUNNING (PID {proc.pid})")
    return {"proc": proc, "lf": lf, "log": log_path, "start": time.time(), "out": out_dir}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--wave", type=int, default=0)
    args = ap.parse_args()
    global DELIVERABLE
    task_set = TASKS
    if args.wave == 1:
        task_set, DELIVERABLE = TASKS_W1, "report.md"
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    tasks = [t for t in task_set if not only or t["id"] in only]

    print("=" * 78 + "\nBeamNG.Earth Phase 10 orchestrator (RenderShadows stutter, proposal round)\n" + "=" * 78)
    running = {t["id"]: launch(t) for t in tasks}
    results = {}
    last_row = last_hb = time.time()

    while running:
        time.sleep(10)
        t_now = time.time()
        for tid in list(running):
            r = running[tid]
            ret = r["proc"].poll()
            if ret is None and t_now - r["start"] > TIMEOUT_S:
                r["proc"].kill()
                ret = "timeout"
            if ret is not None:
                r["lf"].close()
                has_prop = os.path.exists(os.path.join(r["out"], DELIVERABLE))
                diffs = [f for f in os.listdir(r["out"]) if f.endswith(".diff")]
                mins = (t_now - r["start"]) / 60
                status = (f"COMPLETED (exit {ret}, {mins:.0f} min, {DELIVERABLE}={'yes' if has_prop else 'NO'}, "
                          f"{len(diffs)} diffs)")
                if ret != 0:
                    status = "FAILED/" + status
                print(f"[{now('%H:%M:%S')}] {tid}: {status}", flush=True)
                set_row_status(tid, status)
                results[tid] = status
                del running[tid]
        if running and t_now - last_row >= ROW_EVERY_S:
            last_row = t_now
            for tid, r in running.items():
                set_row_status(tid, f"RUNNING: {last_status(r['log'])[:60]}", log=False)
        if running and t_now - last_hb >= HEARTBEAT_EVERY_S:
            last_hb = t_now
            hb = [f"> `[{now('%H:%M:%S')}]` Heartbeat:"]
            hb += [f">   * **{tid}**: {last_status(r['log'])}" for tid, r in running.items()]
            append_tracker("\n".join(hb))

    append_tracker(f"> `[{now()}]` All Phase 10 workers finished. Orchestrator consolidation pending.")
    print("\nAll workers finished:")
    for tid, s in results.items():
        print(f"  {tid}: {s}")


if __name__ == "__main__":
    main()
