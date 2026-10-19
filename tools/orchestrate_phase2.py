"""
Phase 2 Orchestrator for BeamNG.Earth:
- TASK-05: Road Streaming Latency Elimination
- TASK-06: Visual Terrain Desync & Road Pokethrough Elimination
- Verification with AGY Argon 4 High
- Mod sync and live reload in BeamNG
"""

import os
import sys
import subprocess
import time
import datetime

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
        "id": "TASK-05",
        "name": "Road Streaming Latency Elimination",
        "files": ["server/earthd.py", "server/roads.py", "mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua", "mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua"],
        "prompt_file": os.path.join(BRAIN_DIR, "scratch", "subagent_task5_road_latency.txt"),
        "log_file": os.path.join(LOGS_DIR, "task05_road_latency.log"),
    },
    {
        "id": "TASK-06",
        "name": "Visual Terrain Desync & Road Pokethrough Elimination",
        "files": ["server/grading.py", "server/blockworker.py", "server/earthd.py", "mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua"],
        "prompt_file": os.path.join(BRAIN_DIR, "scratch", "subagent_task6_terrain_pokethrough.txt"),
        "log_file": os.path.join(LOGS_DIR, "task06_terrain_pokethrough.log"),
    },
]

def append_tracker(msg):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n\n### Phase 2 Update [{now_str}]\n{msg}\n"
    for p in [TRACKER_REPO, TRACKER_BRAIN]:
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            print(f"Error appending tracker {p}: {e}")

def run_task(task):
    tid = task["id"]
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Starting {tid} ({task['name']})...")
    append_tracker(f"**{tid}** ({task['name']}): RUNNING with `gemini-4-argon-medium`")
    
    prompt = open(task["prompt_file"], "r", encoding="utf-8").read()
    with open(task["log_file"], "w", encoding="utf-8") as lf:
        cmd = [
            AGY_EXE,
            "--model", "gemini-4-argon-medium",
            "--dangerously-skip-permissions",
            "-p", prompt
        ]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, stdout=lf, stderr=subprocess.STDOUT)
    
    if proc.returncode == 0:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {tid} COMPLETED successfully.")
        append_tracker(f"**{tid}** ({task['name']}): COMPLETED (Exit Code 0)")
        return True
    else:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {tid} FAILED (Exit Code {proc.returncode}).")
        append_tracker(f"**{tid}** ({task['name']}): FAILED (Exit Code {proc.returncode})")
        return False

def main():
    print("=" * 70)
    print("BeamNG.Earth Phase 2 Optimization Orchestrator Starting")
    print("=" * 70)

    append_tracker("Starting Phase 2 Implementation Tasks (TASK-05, TASK-06).")

    # Run TASK-05 then TASK-06
    for t in TASKS:
        ok = run_task(t)
        if not ok:
            print(f"Aborting Phase 2 due to failure in {t['id']}")
            return

    # Run test suite
    print("\nRunning unit test suite...")
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = f"{os.path.join(REPO_ROOT, 'server', 'tests')};{os.path.join(REPO_ROOT, 'server')}"
    test_cmd = [
        sys.executable,
        "-m", "unittest",
        "server/tests/test_roads.py",
        "server/tests/test_furniture.py",
        "server/tests/test_buildings.py",
        "server/tests/test_grading.py",
        "server/tests/test_roadmesh.py",
        "server/tests/test_fast.py"
    ]
    test_proc = subprocess.run(test_cmd, cwd=REPO_ROOT, env=test_env, capture_output=True, text=True)
    print("Unit tests output:\n", test_proc.stdout, test_proc.stderr)

    diff_proc = subprocess.run(["git", "diff", "--stat"], cwd=REPO_ROOT, capture_output=True, text=True)
    diff_stat = diff_proc.stdout

    # Launch Argon 4 High Verifier
    print("\nLaunching AGY Argon 4 High Verification Agent for Phase 2...")
    append_tracker("All Phase 2 sub-agents completed. Launching AGY Argon 4 High verification audit...")

    v_prompt = f"""You are the Lead Verification Agent (Argon 4 High).
Audit the Phase 2 code changes made by the sub-agents on BeamNG.Earth:
- TASK-05: Road Streaming Latency Elimination (server/earthd.py, server/roads.py, mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua, mod/beamng_earth/lua/ge/extensions/beamngEarth/roads.lua)
- TASK-06: Visual Terrain Desync & Road Pokethrough Elimination (server/grading.py, server/blockworker.py, server/earthd.py, mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua)

Git stat:
{diff_stat}

Unit tests summary:
{'PASSED' if test_proc.returncode == 0 else 'FAILED'}
{test_proc.stdout}
{test_proc.stderr}

Please review the modifications in detail:
1. Run `git diff` on modified files.
2. Check for syntax correctness, edge-case bugs, or regressions.
3. Confirm that $env:PYTHONPATH='server/tests;server'; python -m unittest server/tests/test_roads.py server/tests/test_grading.py server/tests/test_roadmesh.py passes.
4. If you find any issues, fix them directly in the files.
5. Provide a verification sign-off report.
"""
    v_log = os.path.join(LOGS_DIR, "phase2_verification_report.md")
    with open(v_log, "w", encoding="utf-8") as vf:
        v_cmd = [
            AGY_EXE,
            "--model", "gemini-4-argon-high",
            "--effort", "high",
            "--dangerously-skip-permissions",
            "-p", v_prompt
        ]
        subprocess.run(v_cmd, cwd=REPO_ROOT, stdout=vf, stderr=subprocess.STDOUT)

    print("Phase 2 Verification agent completed.")
    append_tracker("Phase 2 Verification agent completed. Syncing mod to BeamNG and restarting earthd...")

    # Sync mod to BeamNG
    print("Syncing mod to BeamNG user folder...")
    sync_cmd = ["python", "install.py", "--no-venv"]
    p = subprocess.Popen(sync_cmd, cwd=REPO_ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate(input="y\n")
    print("install.py output:", out)

    append_tracker("Phase 2 Orchestration completed successfully! Ready for in-engine benchmark.")
    print("\nPhase 2 Orchestration run finished.")

if __name__ == "__main__":
    main()
