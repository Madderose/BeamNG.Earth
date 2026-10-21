import json, os, math, statistics as st

path = os.path.expandvars(r"%LOCALAPPDATA%\BeamNG\BeamNG.drive\current\PerfCapture_2026-10-21_12-04-03.bngperfgraph.json")
with open(path, "r") as f:
    d = json.load(f)

fps = d["FPS"]["FPS"]
N = len(fps)
ft = [1000.0 / f if f > 0 else 0 for f in fps]
cpu = d["CPU"]
rs = cpu["RenderShadows"]
lua = cpu["Lua"]
tick = cpu["Ticking"]
fw = cpu["FileWatchers"]
rend = cpu["Render"]
work_keys = [k for k in cpu if k not in ("FPSLimiter",)]
cpu_work = [sum(cpu[k][i] for k in work_keys) for i in range(N)]

t_cum = [0.0] * N
acc = 0.0
for i in range(N):
    t_cum[i] = acc
    acc += ft[i] / 1000.0

# 1. Classify every RenderShadows spike (> 3.0 ms)
rs_spikes = [i for i in range(N) if rs[i] > 3.0]
print(f"Total RenderShadows spikes (>3.0 ms): {len(rs_spikes)} / {N} frames")

# Check same-frame vs lag-1 vs lag-2 triggers
same_lua = sum(1 for i in rs_spikes if lua[i] > 1.5)
lag1_lua = sum(1 for i in rs_spikes if i > 0 and lua[i-1] > 1.5)
same_fw  = sum(1 for i in rs_spikes if fw[i] > 1.0)
lag1_fw  = sum(1 for i in rs_spikes if i > 0 and fw[i-1] > 1.0)
same_tick = sum(1 for i in rs_spikes if tick[i] > 1.0)
lag1_tick = sum(1 for i in rs_spikes if i > 0 and tick[i-1] > 1.0)
lag1_rs  = sum(1 for i in rs_spikes if i > 0 and rs[i-1] > 3.0)

print(f"Among {len(rs_spikes)} RenderShadows > 3ms frames:")
print(f"  Same-frame Lua > 1.5ms        : {same_lua} ({100*same_lua/len(rs_spikes):.1f}%)")
print(f"  Prev-frame (lag-1) Lua > 1.5ms: {lag1_lua} ({100*lag1_lua/len(rs_spikes):.1f}%)")
print(f"  Same-frame FileWatchers > 1ms : {same_fw} ({100*same_fw/len(rs_spikes):.1f}%)")
print(f"  Prev-frame (lag-1) Tick > 1ms : {lag1_tick} ({100*lag1_tick/len(rs_spikes):.1f}%)")
print(f"  Prev-frame (lag-1) RShad > 3ms: {lag1_rs} ({100*lag1_rs/len(rs_spikes):.1f}%) (consecutive burst frames)")

# Look at what happens when Lua > 3.0ms: what is RenderShadows on frame t, t+1, t+2?
lua_spikes = [i for i in range(N - 3) if lua[i] > 3.0]
print(f"\nWhen Lua[t] > 3.0ms (n={len(lua_spikes)} frames):")
for offset in (-1, 0, 1, 2, 3):
    vals = [rs[i + offset] for i in lua_spikes if 0 <= i + offset < N]
    print(f"  RenderShadows[t{offset:+d}]: mean={st.mean(vals):.2f}ms, median={st.median(vals):.2f}ms, p90={sorted(vals)[int(0.9*len(vals))]:.2f}ms, >3ms={sum(1 for v in vals if v > 3.0)}/{len(vals)}")

# Look at what happens when Ticking > 1.5ms: what is RenderShadows on frame t, t+1, t+2?
tick_spikes = [i for i in range(N - 3) if tick[i] > 1.5]
print(f"\nWhen Ticking[t] > 1.5ms (n={len(tick_spikes)} frames):")
for offset in (-1, 0, 1, 2, 3):
    vals = [rs[i + offset] for i in tick_spikes if 0 <= i + offset < N]
    print(f"  RenderShadows[t{offset:+d}]: mean={st.mean(vals):.2f}ms, median={st.median(vals):.2f}ms, p90={sorted(vals)[int(0.9*len(vals))]:.2f}ms, >3ms={sum(1 for v in vals if v > 3.0)}/{len(vals)}")

# Look at contiguous runs of RenderShadows > 3.0ms: length of runs and decay profile
runs = []
cur = []
for i in range(N):
    if rs[i] > 3.0:
        cur.append(i)
    else:
        if cur:
            runs.append(cur)
            cur = []
if cur: runs.append(cur)

print(f"\nContiguous runs of RenderShadows > 3.0ms: {len(runs)} runs")
for r in runs:
    vals = [round(rs[i], 2) for i in r]
    lvals = [round(lua[i], 2) for i in r]
    fwvals = [round(fw[i], 2) for i in r]
    tvals = [round(tick[i], 2) for i in r]
    prev_i = r[0] - 1
    p_lua = round(lua[prev_i], 2) if prev_i >= 0 else 0
    p_tick = round(tick[prev_i], 2) if prev_i >= 0 else 0
    print(f"  frames {r[0]}..{r[-1]} (t={t_cum[r[0]]:.2f}s, len={len(r)}): RShad={vals} | Lua={lvals} (prev={p_lua}) | FW={fwvals} | Tick={tvals} (prev={p_tick})")
