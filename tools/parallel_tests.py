#!/usr/bin/env python3
"""High-speed parallel test runner for BeamNG.Earth server tests."""
import os
import sys
import time
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.join(REPO_ROOT, "server", "tests")

# Core test files covering all optimization areas (Phase 1, 2, 3)
CORE_TESTS = [
    "test_roads.py",
    "test_furniture.py",
    "test_buildings.py",
    "test_grading.py",
    "test_roadmesh.py",
    "test_fast.py",
    "test_blockworker.py",
    "test_protocol_agreement.py",
    "test_vegetation.py",
    "test_sidewalk_collision.py",
    "test_dem.py",
    "test_surface.py",
    "test_seacarve.py",
]

def run_single_test(test_file):
    t0 = time.time()
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{TESTS_DIR};{os.path.join(REPO_ROOT, 'server')}"
    
    cmd = [sys.executable, "-m", "unittest", f"server/tests/{test_file}"]
    p = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    dt = time.time() - t0
    
    # Parse test count from output
    count = 0
    for line in p.stderr.splitlines():
        if line.startswith("Ran ") and " tests in " in line:
            try:
                count = int(line.split()[1])
            except ValueError:
                pass
                
    return {
        "file": test_file,
        "success": (p.returncode == 0),
        "returncode": p.returncode,
        "duration": dt,
        "count": count,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }

def main():
    args = sys.argv[1:]
    if "--all" in args:
        test_files = [f for f in os.listdir(TESTS_DIR) if f.startswith("test_") and f.endswith(".py")]
        # Exclude slow socket-hang tests in parallel run
        excluded = {"test_integration_drive.py", "test_benchmark_tool.py"}
        test_files = [f for f in test_files if f not in excluded]
    else:
        test_files = CORE_TESTS

    workers = min(os.cpu_count() or 4, len(test_files))
    print(f"======================================================================")
    print(f"  BeamNG.Earth Parallel Test Runner ({len(test_files)} suites on {workers} parallel workers)")
    print(f"======================================================================\n", flush=True)

    t_start = time.time()
    passed = 0
    failed = 0
    total_tests = 0
    failures = []

    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(run_single_test, f): f for f in test_files}
        for future in as_completed(future_map):
            res = future.result()
            f_name = res["file"]
            dt = res["duration"]
            n = res["count"]
            total_tests += n
            
            if res["success"]:
                passed += 1
                status = "PASS"
                print(f"  [{status}] {f_name:<28} ({n:>3} tests) in {dt:>5.2f}s", flush=True)
            else:
                failed += 1
                status = "FAIL"
                print(f"  [{status}] {f_name:<28} (code {res['returncode']}) in {dt:>5.2f}s", flush=True)
                failures.append(res)

    total_time = time.time() - t_start
    print(f"\n----------------------------------------------------------------------")
    print(f"Results: {passed} passed, {failed} failed | {total_tests} individual tests in {total_time:.2f}s")
    print(f"----------------------------------------------------------------------")

    if failures:
        print("\nFailures Detail:")
        for fail in failures:
            print(f"\n--- {fail['file']} ---")
            print(fail["stderr"][-800:] if len(fail["stderr"]) > 800 else fail["stderr"])
        sys.exit(1)
    else:
        print("\nALL SUITES PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    main()
