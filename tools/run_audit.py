import os
import sys
import subprocess

REPO_ROOT = r"C:\Users\hoppj\SynologyDrive\01_Projets\Projet_BeamEarth\BeamNG.Earth"
BRAIN_DIR = r"C:\Users\hoppj\.gemini\antigravity-ide\brain\05d2526d-883e-4188-9e99-4ba337a6c798"
AGY_EXE = r"C:\Users\hoppj\AppData\Local\agy\bin\agy.exe"

prompt_file = os.path.join(BRAIN_DIR, "scratch", "investigate_roads_and_terrain.txt")
with open(prompt_file, "r", encoding="utf-8") as f:
    prompt = f.read()

cmd = [
    AGY_EXE,
    "--model", "gemini-4-argon-high",
    "--effort", "high",
    "--dangerously-skip-permissions",
    "-p", prompt
]

print("Launching AGY Argon 4 High deep audit...")
sys.stdout.flush()

out_file = os.path.join(REPO_ROOT, "road_and_terrain_audit.md")
with open(out_file, "w", encoding="utf-8") as out:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, stdout=out, stderr=subprocess.STDOUT)

print(f"Audit completed with exit code {proc.returncode}. Report saved to {out_file}.")
