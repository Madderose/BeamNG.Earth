"""
Orchestrator for BeamNG.Earth Performance & Quality Optimizations
Runs parallel AGY Gemini Medium sub-agents for implementation,
tracks task status in task_tracker.md,
and verifies results using an AGY Argon 4 High verification agent.
"""

import sys
import os
import subprocess
import time
import datetime
import shutil

REPO_ROOT = r"C:\Users\hoppj\SynologyDrive\01_Projets\Projet_BeamEarth\BeamNG.Earth"
BRAIN_DIR = r"C:\Users\hoppj\.gemini\antigravity-ide\brain\05d2526d-883e-4188-9e99-4ba337a6c798"
AGY_EXE = r"C:\Users\hoppj\AppData\Local\agy\bin\agy.exe"

LOGS_DIR = os.path.join(REPO_ROOT, "runs", "optimization_logs")
os.makedirs(LOGS_DIR, exist_ok=True)

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

TRACKER_REPO = os.path.join(REPO_ROOT, "task_tracker.md")
TRACKER_BRAIN = os.path.join(BRAIN_DIR, "task_tracker.md")

TASKS = [
    {
        "id": "TASK-01",
        "name": "Streaming & Road Look-Ahead",
        "files": ["server/roads.py", "server/roadmesh.py", "mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua"],
        "prompt_file": os.path.join(BRAIN_DIR, "scratch", "subagent_task1_roads.txt"),
        "log_file": os.path.join(LOGS_DIR, "task01_roads.log"),
    },
    {
        "id": "TASK-02",
        "name": "Object Heights & Furniture/Vegetation",
        "files": ["server/furniture.py", "server/earthd.py"],
        "prompt_file": os.path.join(BRAIN_DIR, "scratch", "subagent_task2_furniture_veg.txt"),
        "log_file": os.path.join(LOGS_DIR, "task02_furniture_veg.log"),
    },
    {
        "id": "TASK-03",
        "name": "Building Scale & Footprints",
        "files": ["server/buildings.py"],
        "prompt_file": os.path.join(BRAIN_DIR, "scratch", "subagent_task3_buildings.txt"),
        "log_file": os.path.join(LOGS_DIR, "task03_buildings.log"),
    },
    {
        "id": "TASK-04",
        "name": "Native Kernels & Fast Fallbacks",
        "files": ["native/earthfast/src/lib.rs", "server/fast.py"],
        "prompt_file": os.path.join(BRAIN_DIR, "scratch", "subagent_task4_native.txt"),
        "log_file": os.path.join(LOGS_DIR, "task04_native.log"),
    },
]

def update_tracker(status_dict, verification_text="Pending"):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# BeamNG.Earth: Master Optimization Task Tracker",
        "",
        "**Orchestrator**: AGY Argon 4 High  ",
        "**Verification Agent**: AGY Argon 4 High (`gemini-4-argon-high`, effort=high)  ",
        "**Sub-Agents**: AGY Gemini Medium (`gemini-4-argon-medium`)  ",
        f"**Last Updated**: {now_str}  ",
        "",
        "---",
        "",
        "## Sub-Agent Parallel Execution Status",
        "",
        "| Task ID | Component / Area | Files Allocated | Model | Execution Status | Output Log |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for t in TASKS:
        tid = t["id"]
        status = status_dict.get(tid, "NOT STARTED")
        files_str = "<br>".join([f"`{f}`" for f in t["files"]])
        log_rel = os.path.relpath(t["log_file"], REPO_ROOT).replace("\\", "/")
        lines.append(f"| **{tid}** | **{t['name']}** | {files_str} | `gemini-4-argon-medium` | **{status}** | [`{log_rel}`]({log_rel}) |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Verification Review (Argon 4 High)",
        "",
        verification_text,
        "",
    ])
    
    content = "\n".join(lines)
    for p in [TRACKER_REPO, TRACKER_BRAIN]:
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Error writing tracker to {p}: {e}")

def main():
    print("=" * 70)
    print("BeamNG.Earth Optimization Orchestrator Starting")
    print("=" * 70)

    task_status = {t["id"]: "PENDING" for t in TASKS}
    update_tracker(task_status, "Awaiting completion of sub-agents.")

    # Start all 4 sub-agents in parallel
    processes = {}
    log_handles = {}

    for t in TASKS:
        tid = t["id"]
        prompt_content = open(t["prompt_file"], "r", encoding="utf-8").read()
        log_f = open(t["log_file"], "w", encoding="utf-8")
        log_handles[tid] = log_f

        cmd = [
            AGY_EXE,
            "--model", "gemini-4-argon-medium",
            "--dangerously-skip-permissions",
            "-p", prompt_content
        ]

        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Launching {tid} ({t['name']}) with gemini-4-argon-medium...")
        proc = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            shell=False
        )
        processes[tid] = proc
        task_status[tid] = f"RUNNING (PID {proc.pid})"

    update_tracker(task_status, "All 4 sub-agents running in parallel.")

    # Monitor processes until all finish
    active = set(processes.keys())
    while active:
        time.sleep(3)
        for tid in list(active):
            proc = processes[tid]
            ret = proc.poll()
            if ret is not None:
                log_handles[tid].close()
                active.remove(tid)
                if ret == 0:
                    task_status[tid] = "COMPLETED (Exit Code 0)"
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {tid} COMPLETED successfully.")
                else:
                    task_status[tid] = f"FAILED (Exit Code {ret})"
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {tid} FAILED with exit code {ret}.")
                update_tracker(task_status, f"In progress ({len(TASKS) - len(active)}/{len(TASKS)} completed).")

    print("\nAll sub-agents finished. Running unit tests...")
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = f"{os.path.join(REPO_ROOT, 'server', 'tests')};{os.path.join(REPO_ROOT, 'server')}"
    
    test_cmd = [
        sys.executable,
        "-m", "unittest",
        "server/tests/test_roads.py",
        "server/tests/test_furniture.py",
        "server/tests/test_buildings.py"
    ]
    test_proc = subprocess.run(test_cmd, cwd=REPO_ROOT, env=test_env, capture_output=True, text=True)
    print("Unit test output:\n", test_proc.stdout, test_proc.stderr)
    test_summary = f"Unit Tests Result: {'PASSED' if test_proc.returncode == 0 else 'FAILED'}\n```\n{test_proc.stdout}\n{test_proc.stderr}\n```"

    # Capture git diff
    diff_proc = subprocess.run(["git", "diff", "--stat"], cwd=REPO_ROOT, capture_output=True, text=True)
    diff_stat = diff_proc.stdout

    # Now launch Argon 4 High Verifier
    print("\nLaunching AGY Argon 4 High Verification Agent...")
    update_tracker(task_status, "Sub-agents complete. Running Argon 4 High verification audit...")

    verify_prompt = f"""You are the Lead Verification Agent (Argon 4 High).
You are reviewing the code changes made by 4 parallel sub-agents on BeamNG.Earth:
1. TASK-01: Streaming & Road Priority (server/roads.py, server/roadmesh.py, mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua)
2. TASK-02: Object Heights & Vegetation Grader Integration (server/furniture.py, server/earthd.py)
3. TASK-03: Building Scale, Height & Footprint Fixes (server/buildings.py)
4. TASK-04: Native Kernels & Fast Fallbacks (native/earthfast/src/lib.rs, server/fast.py)

Here is git status and stat:
{diff_stat}

Unit tests summary:
{test_summary}

Please review the modifications in detail:
1. Run `git diff` on each modified file using terminal tools.
2. Check for syntax correctness, edge-case bugs, potential regressions, division-by-zero, out-of-bounds, or NaN values.
3. Verify that the Golden Principles from docs/ROADMAP.md are preserved (deterministic generation, <8192 tris per mesh, frame safety).
4. Run `$env:PYTHONPATH='server/tests;server'; python -m unittest server/tests/test_roads.py server/tests/test_furniture.py server/tests/test_buildings.py` to confirm tests pass.
5. If you identify any bugs or regressions, fix them directly in the files.
6. Provide a concise verification sign-off report detailing what was audited and confirmed.
"""
    verify_log_path = os.path.join(LOGS_DIR, "verification_report.md")
    with open(verify_log_path, "w", encoding="utf-8") as vf:
        v_cmd = [
            AGY_EXE,
            "--model", "gemini-4-argon-high",
            "--effort", "high",
            "--dangerously-skip-permissions",
            "-p", verify_prompt
        ]
        v_proc = subprocess.run(v_cmd, cwd=REPO_ROOT, stdout=vf, stderr=subprocess.STDOUT)
    
    print("Verification agent completed.")
    if os.path.exists(verify_log_path):
        verify_report = open(verify_log_path, "r", encoding="utf-8").read()
    else:
        verify_report = "Verification log not generated."

    update_tracker(task_status, f"### Verification Sign-Off\n\n{verify_report[:4000]}")
    print("\nOrchestration run completed successfully!")

if __name__ == "__main__":
    main()
