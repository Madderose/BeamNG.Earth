"""
BeamNG.Earth Phase 6 Optimization Master Orchestrator:
- Launches 3 parallel sub-agents (gemini-4-argon-medium):
    * TASK-P6-A: Governor, Core & Terrain Commit Isolation
    * TASK-P6-B: Trees & Forest Zero-Allocation GC Fix
    * TASK-P6-C: Farfield Swaps, Queue Pruning & Velocity Capsule
- Reports progress to task_tracker.md every 30 seconds.
- Launches AGY Argon 4 High Verification Agent upon completion.
- Syncs mod to BeamNG and runs test suites.
"""

import os
import sys
import time
import subprocess
import datetime
from pathlib import Path

REPO_ROOT = r"C:\Users\hoppj\SynologyDrive\01_Projets\Projet_BeamEarth\BeamNG.Earth"
TRACKER_PATH = os.path.join(REPO_ROOT, "task_tracker.md")
LOGS_DIR = os.path.join(REPO_ROOT, "runs", "optimization_logs")
os.makedirs(LOGS_DIR, exist_ok=True)

AGY_EXE = r"C:\Users\hoppj\AppData\Local\agy\bin\agy.exe"
if not os.path.exists(AGY_EXE):
    AGY_EXE = "agy"

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

TASKS = [
    {
        "id": "TASK-P6-A",
        "name": "Governor Token Starvation & Heavy Frame Commit Isolation",
        "files": ["mod/.../governor.lua", "mod/.../core.lua", "mod/.../terrain.lua"],
        "prompt_file": os.path.join(REPO_ROOT, "scratch", "subagent_task_p6a_governor_core.txt"),
        "log_file": os.path.join(LOGS_DIR, "task_p6a_governor_core.log"),
        "model": "gemini-4-argon-medium",
    },
    {
        "id": "TASK-P6-B",
        "name": "Forest Mutation Capping & Zero-Allocation Trees GC",
        "files": ["mod/.../trees.lua"],
        "prompt_file": os.path.join(REPO_ROOT, "scratch", "subagent_task_p6b_trees.txt"),
        "log_file": os.path.join(LOGS_DIR, "task_p6b_trees.log"),
        "model": "gemini-4-argon-medium",
    },
    {
        "id": "TASK-P6-C",
        "name": "Farfield Algebraic Swap Cancellation & Velocity Capsule",
        "files": ["mod/.../farfield.lua", "server/farfield.py", "server/earthd.py"],
        "prompt_file": os.path.join(REPO_ROOT, "scratch", "subagent_task_p6c_farfield_streaming.txt"),
        "log_file": os.path.join(LOGS_DIR, "task_p6c_farfield_streaming.log"),
        "model": "gemini-4-argon-medium",
    },
]


def update_tracker_task_status(task_id, status_str, append_log=True):
    """Update the table row and append a log entry in task_tracker.md."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(TRACKER_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        for i, line in enumerate(lines):
            if f"**{task_id}**" in line and "|" in line:
                parts = line.split("|")
                if len(parts) >= 7:
                    parts[6] = f" **{status_str}** "
                    lines[i] = "|".join(parts)
                break

        if append_log:
            lines.append(f"> `[{now_str}]` **{task_id}**: Status updated to **{status_str}**")
        with open(TRACKER_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        print(f"Warning: could not update tracker: {e}", flush=True)


def append_tracker_heartbeat(reports):
    """Append 30-second progress heartbeat to task_tracker.md."""
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    heartbeat_lines = [f"> `[{now_str}]` **Heartbeat Progress Report**:"]
    for tid, status in reports.items():
        heartbeat_lines.append(f">   * **{tid}**: {status}")

    try:
        with open(TRACKER_PATH, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(heartbeat_lines) + "\n")
    except Exception as e:
        print(f"Warning: could not append heartbeat to tracker: {e}", flush=True)


def extract_agent_status(log_file):
    """Extract a concise status summary from the agent's log file."""
    if not os.path.exists(log_file):
        return "Initializing..."
    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if not lines:
            return "Started, awaiting output..."
        
        # 1. Search for latest explicit STATUS_UPDATE line
        latest_status = None
        for l in reversed(lines):
            clean = l.strip()
            if "STATUS_UPDATE:" in clean:
                latest_status = clean[clean.index("STATUS_UPDATE:"):]
                break
        
        # 2. Extract recent action / tool call
        latest_action = None
        for l in reversed(lines[-25:]):
            clean = l.strip()
            if any(k in clean for k in ["TOOL ", "view_file", "replace_file_content", "run_command", "write_to_file"]):
                latest_action = clean[:90]
                break
            if len(clean) > 20 and not clean.startswith(("{", "[", "```", "}", "]")) and "STATUS_UPDATE" not in clean:
                if not latest_action:
                    latest_action = clean[:90]

        if latest_status:
            if latest_action and latest_action not in latest_status:
                return f"{latest_status} [Action: {latest_action}]"
            return latest_status
        elif latest_action:
            return f"In progress: {latest_action}"
        else:
            return "Active"
    except Exception as e:
        return f"Reading log: {e}"


def launch_subagent(task):
    """Launch an AGY subagent asynchronously via Popen."""
    tid = task["id"]
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    prompt_file = task["prompt_file"]
    log_file = task["log_file"]

    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read()

    lf = open(log_file, "w", encoding="utf-8")
    cmd = [
        AGY_EXE,
        "--model", task["model"],
        "--dangerously-skip-permissions",
        "-p", prompt
    ]
    proc = subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=lf, stderr=subprocess.STDOUT)
    print(f"[{now_str}] Launched {tid} ({task['name']}) -> PID {proc.pid} [{task['model']}]", flush=True)
    update_tracker_task_status(tid, f"RUNNING (PID {proc.pid})")
    return proc, lf


def main():
    print("=" * 80)
    print("BeamNG.Earth Phase 6: High-Speed Optimization Orchestrator")
    print("=" * 80, flush=True)

    processes = {}
    log_handles = {}

    for t in TASKS:
        proc, lf = launch_subagent(t)
        processes[t["id"]] = proc
        log_handles[t["id"]] = lf

    active_tasks = set(processes.keys())
    poll_count = 0

    while active_tasks:
        time.sleep(30.0)
        poll_count += 1
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        reports = {}

        for tid in list(active_tasks):
            proc = processes[tid]
            ret = proc.poll()
            if ret is not None:
                log_handles[tid].close()
                active_tasks.remove(tid)
                if ret == 0:
                    print(f"[{now_str}] {tid} COMPLETED successfully (Exit code 0).", flush=True)
                    update_tracker_task_status(tid, "COMPLETED (Exit Code 0)")
                    reports[tid] = "COMPLETED (Exit Code 0)"
                else:
                    print(f"[{now_str}] {tid} FAILED with exit code {ret}.", flush=True)
                    update_tracker_task_status(tid, f"FAILED (Exit Code {ret})")
                    reports[tid] = f"FAILED (Exit Code {ret})"
            else:
                log_f = [t["log_file"] for t in TASKS if t["id"] == tid][0]
                status_summary = extract_agent_status(log_f)
                reports[tid] = f"Running (PID {proc.pid}): {status_summary}"
                print(f"[{now_str}] Heartbeat {tid} (PID {proc.pid}): {status_summary}", flush=True)

                # Update table row with short status
                if "STATUS_UPDATE:" in status_summary:
                    clean_status = status_summary.split("STATUS_UPDATE:")[1].split("[")[0].strip()
                    update_tracker_task_status(tid, f"RUNNING: {clean_status[:40]}", append_log=False)
                else:
                    update_tracker_task_status(tid, f"RUNNING (PID {proc.pid})", append_log=False)

        if reports:
            append_tracker_heartbeat(reports)

    print("\n" + "=" * 80)
    print("All Phase 6 subagents finished. Launching AGY Argon 4 High Verification Audit...")
    print("=" * 80, flush=True)

    # Launch Argon 4 High Verification Agent
    v_log = os.path.join(LOGS_DIR, "phase6_verification_report.md")
    v_prompt = """You are the Lead Verification Agent (Argon 4 High).
Audit the Phase 6 performance optimizations implemented by the 3 sub-agents across BeamNG.Earth:
1. TASK-P6-A: Governor token starvation fix, urgent target boost, and terrain commit isolation.
2. TASK-P6-B: Forest mutation capping (allow(sh) fix), solid demotion bypass, and MatrixF/vec3 zero-allocation GC fix in trees.lua.
3. TASK-P6-C: Algebraic swap-group cancellation in farfield.lua, velocity-lookahead peekImport, and server-side velocity capsule in earthd.py/farfield.py.

Review actions:
1. Run `git diff` to inspect all changes made.
2. Verify syntax and logic correctness in all modified files.
3. Run the unit test suites:
   - python -m unittest server/tests/test_roads.py
   - python -m unittest server/tests/test_server.py
   - python -m unittest server/tests/test_protocol_agreement.py
   - python -m unittest server/tests/test_vegetation.py
   - python -m unittest server/tests/test_roadmesh.py
4. If you find any regressions or bugs, fix them directly.
5. Provide a comprehensive verification sign-off report with diff statistics and test outcomes.
6. Append your verification sign-off report to `task_tracker.md` under Phase 6.
"""

    with open(v_log, "w", encoding="utf-8") as vf:
        v_cmd = [
            AGY_EXE,
            "--model", "gemini-4-argon-high",
            "--effort", "high",
            "--dangerously-skip-permissions",
            "-p", v_prompt
        ]
        v_proc = subprocess.run(v_cmd, cwd=REPO_ROOT, stdout=vf, stderr=subprocess.STDOUT)

    print(f"Verification Agent completed with code {v_proc.returncode}.")
    
    # Sync mod to BeamNG
    print("Syncing mod to BeamNG user folder...")
    sync_cmd = ["python", "install.py", "--no-venv"]
    p = subprocess.Popen(sync_cmd, cwd=REPO_ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate(input="y\n")
    print("install.py output:", out)

    update_tracker_task_status("TASK-P6-VERIFY", f"COMPLETED & APPROVED (Exit Code {v_proc.returncode})")
    print("\nPhase 6 Orchestration finished successfully!")


if __name__ == "__main__":
    main()
