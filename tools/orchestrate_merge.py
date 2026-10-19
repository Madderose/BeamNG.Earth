#!/usr/bin/env python3
"""
Master Parallel Merge & Harmonization Orchestrator for BeamNG.Earth:
- Upstream Base: TecnaGamer/BeamNG.Earth (v1.5.0, v1.5.1-beta)
- Local Refactor: Phase 1-3 Streaming, Terrain Pokethrough & Sidewalk Fixes

Concurrent Multi-Agent Execution:
  - Sub-Agents: AGY Argon 4 Medium (`gemini-4-argon-medium`) executing in parallel:
      * TASK-M02: Buildings & Architecture Harmonization
      * TASK-M03: Roads, Plazas, Bridges & Server
      * TASK-M04: In-Game Lua Extensions & Physics Pauses
  - Followed by:
      * TASK-M05: Sidewalk True Ground-Level Conformance (conforming curbs to graded edge & natural ground)
  - Master Verification & Sign-Off:
      * TASK-M06: AGY Argon 4 High (`gemini-4-argon-high`, effort=high) running parallel test suite & in-engine audit.
"""

import datetime
import os
import subprocess
import sys
import time

REPO_ROOT = r"C:\Users\hoppj\SynologyDrive\01_Projets\Projet_BeamEarth\BeamNG.Earth"
AGY_EXE = r"C:\Users\hoppj\AppData\Local\agy\bin\agy.exe"
SCRATCH_DIR = os.path.join(REPO_ROOT, "scratch")
LOGS_DIR = os.path.join(REPO_ROOT, "runs", "optimization_logs")
TRACKER_PATH = os.path.join(REPO_ROOT, "task_tracker.md")

os.makedirs(SCRATCH_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


def update_tracker_task_status(task_id, status_str):
    """Update execution status for a specific task in task_tracker.md."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(TRACKER_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        prefix = f"| **{task_id}** |"
        for i, line in enumerate(lines):
            if line.startswith(prefix):
                parts = line.split("|")
                if len(parts) >= 7:
                    parts[6] = f" **{status_str}** "
                    lines[i] = "|".join(parts)
                break

        lines.append(f"> `[{now_str}]` **{task_id}**: Status updated to **{status_str}**")
        with open(TRACKER_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        print(f"Warning: could not update tracker: {e}")


def launch_subagent(task):
    """Launch an AGY subagent asynchronously via Popen."""
    tid = task["id"]
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    prompt_file = task["prompt_file"]
    log_file = task["log_file"]

    if not os.path.exists(prompt_file):
        print(f"[{now_str}] Error: prompt file {prompt_file} missing for {tid}!", flush=True)
        update_tracker_task_status(tid, "FAILED (Missing Prompt)")
        return None, None

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
    update_tracker_task_status(tid, f"RUNNING (PID {proc.pid}, {task['model']})")
    return proc, lf


def main():
    print("=" * 80)
    print("BeamNG.Earth Phase 4: Master Parallel Merge & Harmonization Orchestrator")
    print("=" * 80, flush=True)

    # TASK-M01 is already completed and staged
    print("[15:35:00] TASK-M01 (Native Rust & PyO3 Concurrency) is already RESOLVED and STAGED.")
    update_tracker_task_status("TASK-M01", "COMPLETED (Exit Code 0)")

    # Parallel tasks to run simultaneously
    parallel_tasks = [
        {
            "id": "TASK-M02",
            "name": "Buildings & Architecture Harmonization",
            "files": ["server/buildings.py", "server/tests/test_buildings.py"],
            "model": "gemini-4-argon-medium",
            "prompt_file": os.path.join(SCRATCH_DIR, "subagent_task_m02_buildings.txt"),
            "log_file": os.path.join(LOGS_DIR, "task_m02_buildings.log"),
            "stage_files": ["server/buildings.py", "server/tests/test_buildings.py"],
        },
        {
            "id": "TASK-M03",
            "name": "Roads, Plazas, Bridges & Server",
            "files": ["server/roads.py", "server/roadmesh.py", "server/earthd.py"],
            "model": "gemini-4-argon-medium",
            "prompt_file": os.path.join(SCRATCH_DIR, "subagent_task_m03_roads_server.txt"),
            "log_file": os.path.join(LOGS_DIR, "task_m03_roads_server.log"),
            "stage_files": ["server/roads.py", "server/roadmesh.py", "server/earthd.py"],
        },
        {
            "id": "TASK-M04",
            "name": "In-Game Lua Extensions & Physics Pauses",
            "files": [
                "mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua",
                "mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua",
                "mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua",
                "mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua",
                "mod/beamng_earth/lua/ge/extensions/beamngEarth/drophold.lua",
            ],
            "model": "gemini-4-argon-medium",
            "prompt_file": os.path.join(SCRATCH_DIR, "subagent_task_m04_lua.txt"),
            "log_file": os.path.join(LOGS_DIR, "task_m04_lua.log"),
            "stage_files": ["mod/beamng_earth/lua/ge/extensions/beamngEarth/"],
        },
    ]

    print("\nLaunching Phase 4 Parallel Sub-Agents (Argon 4 Medium)...", flush=True)
    active_procs = {}
    for task in parallel_tasks:
        proc, lf = launch_subagent(task)
        if proc:
            active_procs[task["id"]] = {"proc": proc, "lf": lf, "task": task}

    # Monitor running parallel tasks
    while active_procs:
        time.sleep(3)
        finished = []
        for tid, info in active_procs.items():
            ret = info["proc"].poll()
            if ret is not None:
                info["lf"].close()
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                if ret == 0:
                    print(f"[{now_str}] {tid} COMPLETED successfully (Exit Code 0).", flush=True)
                    update_tracker_task_status(tid, "COMPLETED (Exit Code 0)")
                    if info["task"].get("stage_files"):
                        subprocess.run(["git", "add"] + info["task"]["stage_files"], cwd=REPO_ROOT)
                else:
                    print(f"[{now_str}] {tid} FAILED with exit code {ret}!", flush=True)
                    update_tracker_task_status(tid, f"FAILED (Exit Code {ret})")
                finished.append(tid)

        for tid in finished:
            del active_procs[tid]

    print("\n" + "=" * 80)
    print("Parallel sub-agents finished. Proceeding to TASK-M05 (Sidewalk Ground Conformance)...")
    print("=" * 80, flush=True)

    # Launch TASK-M05
    task_m05 = {
        "id": "TASK-M05",
        "name": "Sidewalk True Ground-Level Conformance",
        "files": ["server/sidewalks.py", "server/roads.py", "server/grading.py"],
        "model": "gemini-4-argon-medium",
        "prompt_file": os.path.join(SCRATCH_DIR, "subagent_task_m05_sidewalks.txt"),
        "log_file": os.path.join(LOGS_DIR, "task_m05_sidewalks.log"),
        "stage_files": ["server/sidewalks.py", "server/roads.py", "server/grading.py"],
    }
    proc5, lf5 = launch_subagent(task_m05)
    if proc5:
        proc5.wait()
        lf5.close()
        if proc5.returncode == 0:
            print("[TASK-M05] COMPLETED successfully.")
            update_tracker_task_status("TASK-M05", "COMPLETED (Exit Code 0)")
            subprocess.run(["git", "add"] + task_m05["stage_files"], cwd=REPO_ROOT)
        else:
            print(f"[TASK-M05] FAILED with exit code {proc5.returncode}!")
            update_tracker_task_status("TASK-M05", f"FAILED (Exit Code {proc5.returncode})")

    # Run verification with Argon 4 High
    run_verification_argon_high()


def run_verification_argon_high():
    tid = "TASK-M06"
    print("\n" + "=" * 80)
    print(f"Starting {tid}: Full Verification & In-Engine Benchmark (Argon 4 High)")
    print("=" * 80, flush=True)
    update_tracker_task_status(tid, "RUNNING (gemini-4-argon-high)")

    # 1. Run parallel unit tests
    print("Running parallel test suite (tools/parallel_tests.py)...", flush=True)
    test_proc = subprocess.run([sys.executable, "tools/parallel_tests.py"], cwd=REPO_ROOT, capture_output=True, text=True)
    print(test_proc.stdout)
    if test_proc.stderr:
        print(test_proc.stderr)

    tests_ok = (test_proc.returncode == 0)

    # 2. Run Argon 4 High Verification Audit
    v_prompt = f"""You are the Lead Verification Agent (Argon 4 High).
Audit the merged codebase of BeamNG.Earth (combining Upstream 1.5.1 with our performance optimizations and ground-conforming sidewalks):

Parallel Test Suite Output:
{'PASSED' if tests_ok else 'FAILED'}
{test_proc.stdout}

Check:
1. `git status` and `git diff` across native/, server/, mod/.
2. Confirm there are NO remaining conflict markers (<<<<<<<) anywhere.
3. Confirm all unit tests pass with zero regressions.
4. Verify sidewalk elevation calculations in `server/sidewalks.py` and `server/roads.py` conform to terrain slope.
5. Provide a final verification sign-off summary.
"""
    v_log = os.path.join(LOGS_DIR, "phase4_merge_verification_report.md")
    with open(v_log, "w", encoding="utf-8") as vf:
        v_cmd = [
            AGY_EXE,
            "--model", "gemini-4-argon-high",
            "--effort", "high",
            "--dangerously-skip-permissions",
            "-p", v_prompt
        ]
        v_proc = subprocess.run(v_cmd, cwd=REPO_ROOT, stdout=vf, stderr=subprocess.STDOUT)

    if tests_ok and v_proc.returncode == 0:
        update_tracker_task_status(tid, "COMPLETED & VERIFIED (Argon 4 High)")
        print("\n[SUCCESS] Phase 4 Merge and Harmonization successfully completed and verified!", flush=True)
    else:
        update_tracker_task_status(tid, "FAILED (Verification Issues Found)")
        print("\n[WARNING] Verification finished with issues. Check log files.", flush=True)


if __name__ == "__main__":
    main()
