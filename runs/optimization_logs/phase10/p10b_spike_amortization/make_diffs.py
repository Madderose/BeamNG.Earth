import subprocess

OUT_DIR = "runs/optimization_logs/phase10/p10b_spike_amortization"
TARGETS = [
    ("mod/beamng_earth/lua/ge/extensions/beamngEarth/governor.lua", f"{OUT_DIR}/copies/governor.lua", f"{OUT_DIR}/governor.lua.diff"),
    ("mod/beamng_earth/lua/ge/extensions/beamngEarth/core.lua",     f"{OUT_DIR}/copies/core.lua",     f"{OUT_DIR}/core.lua.diff"),
    ("mod/beamng_earth/lua/ge/extensions/beamngEarth/trees.lua",    f"{OUT_DIR}/copies/trees.lua",    f"{OUT_DIR}/trees.lua.diff"),
    ("mod/beamng_earth/lua/ge/extensions/beamngEarth/farfield.lua", f"{OUT_DIR}/copies/farfield.lua", f"{OUT_DIR}/farfield.lua.diff"),
    ("mod/tests/test_governor.lua", f"{OUT_DIR}/copies/test_governor.lua", f"{OUT_DIR}/test_governor.lua.diff"),
    ("mod/tests/test_trees.lua",    f"{OUT_DIR}/copies/test_trees.lua",    f"{OUT_DIR}/test_trees.lua.diff"),
    ("mod/tests/test_farfield.lua", f"{OUT_DIR}/copies/test_farfield.lua", f"{OUT_DIR}/test_farfield.lua.diff"),
]

for orig, copy_path, diff_path in TARGETS:
    res = subprocess.run(
        ["git", "diff", "--no-index", "--no-color", "--", orig, copy_path],
        capture_output=True
    )
    raw_bytes = res.stdout
    lines = raw_bytes.splitlines(keepends=True)
    out_lines = []
    for idx, line in enumerate(lines):
        if idx == 0 and line.startswith(b"diff --git "):
            out_lines.append(f"diff --git a/{orig} b/{orig}\n".encode("utf-8"))
        elif idx <= 4 and line.startswith(b"--- a/"):
            out_lines.append(f"--- a/{orig}\n".encode("utf-8"))
        elif idx <= 5 and line.startswith(b"+++ b/"):
            out_lines.append(f"+++ b/{orig}\n".encode("utf-8"))
        else:
            out_lines.append(line)
    with open(diff_path, "wb") as f:
        f.writelines(out_lines)

    chk = subprocess.run(["git", "apply", "--check", diff_path], capture_output=True, text=True)
    if chk.returncode != 0:
        print(f"ERROR checking {diff_path}: {chk.stderr}")
    else:
        print(f"OK: {diff_path} ({len(out_lines)} lines) passes git apply --check")
