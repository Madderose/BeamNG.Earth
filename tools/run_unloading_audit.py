import os
import sys
import subprocess

REPO_ROOT = r"C:\Users\hoppj\SynologyDrive\01_Projets\Projet_BeamEarth\BeamNG.Earth"
PROMPT_FILE = os.path.join(REPO_ROOT, "scratch", "investigate_unloading_and_minimap.txt")
AGY_EXE = r"C:\Users\hoppj\AppData\Local\agy\bin\agy.exe"
OUT_FILE = os.path.join(REPO_ROOT, "runs", "optimization_logs", "unloading_and_minimap_audit.md")

with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt = f.read()

cmd = [
    AGY_EXE,
    "--model", "gemini-4-argon-high",
    "--effort", "high",
    "--dangerously-skip-permissions",
    "-p", prompt
]

print("Launching AGY Argon 4 High deep audit on chunk unloading and mini-map sync...")
sys.stdout.flush()

os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as out:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, stdout=out, stderr=subprocess.STDOUT)

print(f"Audit completed with exit code {proc.returncode}. Report saved to {OUT_FILE}.")
