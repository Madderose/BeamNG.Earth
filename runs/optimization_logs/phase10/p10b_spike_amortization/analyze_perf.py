import json, os, sys, math, statistics as st

path = os.path.expandvars(r"%LOCALAPPDATA%\BeamNG\BeamNG.drive\current\PerfCapture_2026-10-21_12-04-03.bngperfgraph.json")
with open(path, "r") as f:
    d = json.load(f)

fps = d["FPS"]["FPS"]
N = len(fps)
ft = [1000.0 / f if f > 0 else 0 for f in fps]
cpu = d["CPU"]
gpu = d["GPU"]
work_keys = [k for k in cpu if k not in ("FPSLimiter",)]
cpu_work = [sum(cpu[k][i] for k in work_keys) for i in range(N)]

print("CPU keys:", sorted(cpu.keys()))
print("GPU keys:", sorted(gpu.keys()))
meds = {k: st.median(cpu[k]) for k in work_keys}
print("Medians:", {k: round(meds[k], 3) for k in ("RenderShadows", "Lua", "Ticking", "FileWatchers", "Render", "PreRender", "Physics", "Input") if k in meds})

# Cumulative time array
t_cum = [0.0] * N
acc = 0.0
for i in range(N):
    t_cum[i] = acc
    acc += ft[i] / 1000.0

def lag_corr(a, b, lag):
    # corr(a[i], b[i + lag]): positive lag means 'a' leads 'b' by `lag` frames
    if lag >= 0:
        xa = a[:N - lag]
        xb = b[lag:]
    else:
        xa = a[-lag:]
        xb = b[:N + lag]
    ma, mb = st.mean(xa), st.mean(xb)
    num = sum((x - ma) * (y - mb) for x, y in zip(xa, xb))
    den = math.sqrt(sum((x - ma) ** 2 for x in xa) * sum((y - mb) ** 2 for y in xb))
    return num / den if den else 0.0

rs = cpu["RenderShadows"]
print("\nCross-correlation with RenderShadows (lag > 0 means X[t] leads RenderShadows[t+lag]):")
for name in ("Lua", "Ticking", "FileWatchers", "PreRender", "Render", "RenderShadows"):
    if name not in cpu: continue
    vals = [f"lag {L:+d}: {lag_corr(cpu[name], rs, L):+.3f}" for L in range(-3, 6)]
    print(f"  {name:15s} -> " + " | ".join(vals))

print("\nFrame-by-frame window 1: t in [8.85s, 9.85s]:")
print(" idx   t(s)   ft    work   RShad   Lua    Tick   FWatch  PreR   Rend   GPU_Shad")
for i in range(N):
    if 8.85 <= t_cum[i] <= 9.85:
        g_sh = gpu.get("ShadowMapPass", [0]*N)[i]
        print(f"{i:4d} {t_cum[i]:6.3f} {ft[i]:5.2f} {cpu_work[i]:6.2f} | {rs[i]:5.2f}  {cpu['Lua'][i]:5.2f}  {cpu['Ticking'][i]:5.2f}  {cpu['FileWatchers'][i]:6.2f}  {cpu.get('PreRender',[0]*N)[i]:5.2f}  {cpu.get('Render',[0]*N)[i]:5.2f} | {g_sh:5.2f}")

print("\nFrame-by-frame window 2: t in [12.25s, 12.85s]:")
print(" idx   t(s)   ft    work   RShad   Lua    Tick   FWatch  PreR   Rend   GPU_Shad")
for i in range(N):
    if 12.25 <= t_cum[i] <= 12.85:
        g_sh = gpu.get("ShadowMapPass", [0]*N)[i]
        print(f"{i:4d} {t_cum[i]:6.3f} {ft[i]:5.2f} {cpu_work[i]:6.2f} | {rs[i]:5.2f}  {cpu['Lua'][i]:5.2f}  {cpu['Ticking'][i]:5.2f}  {cpu['FileWatchers'][i]:6.2f}  {cpu.get('PreRender',[0]*N)[i]:5.2f}  {cpu.get('Render',[0]*N)[i]:5.2f} | {g_sh:5.2f}")

# Also find all frames where RenderShadows > 2.0ms outside those two windows
print("\nOther frames with RenderShadows > 2.0ms:")
for i in range(N):
    if rs[i] > 2.0 and not (8.85 <= t_cum[i] <= 9.85) and not (12.25 <= t_cum[i] <= 12.85):
        print(f"{i:4d} {t_cum[i]:6.3f} {ft[i]:5.2f} {cpu_work[i]:6.2f} | RShad={rs[i]:5.2f} Lua={cpu['Lua'][i]:5.2f} Tick={cpu['Ticking'][i]:5.2f} FW={cpu['FileWatchers'][i]:5.2f}")
