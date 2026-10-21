path = "runs/optimization_logs/phase10/p10b_spike_amortization/copies/test_farfield.lua"
with open(path, "rb") as f:
    raw = f.read()

has_crlf = b"\r\n" in raw
nl = "\r\n" if has_crlf else "\n"
text = raw.decode("utf-8").replace("\r\n", "\n")

old1 = """  farfield.switchAnchor(64, false, { cx = 0, cy = 0 })
  step(free, nil, 100)
end

T.done('test_farfield')"""

new1 = """  farfield.switchAnchor(64, false, { cx = 0, cy = 0 })
  step(free, nil, 100)
end

------------------------------------------------------------------------------------------
-- P10-B: governed reveal cap (REVEALS_PER_FRAME = 2, 1 in burst mode) and no co-scheduling of
-- reveal + import in the same governed frame
do
  farfield.setNearVisual('terrain')
  farfield.switchAnchor(70, false, { cx = 0, cy = 0 })
  -- Preload 3 tiles with free governor so their groups are ready to reveal
  for i = 1, 3 do
    farfield.onTile(tile(70, 0, i + 10, 10))
  end
  step(free, camSouth)
  for i = 1, 3 do
    farfield.onSwap(swap(70, 700 + i, { key(0, i + 10, 10) }))
  end
  -- Also queue a 4th tile that still needs importing
  farfield.onTile(tile(70, 0, 20, 10))

  local gv = governor.new({ clock = clock })
  for _ = 1, 80 do now = now + 10; gv:beginFrame(true, 10.0) end
  gv.burst = true -- burst mode: at most 1 reveal per frame, and no import on a reveal frame
  now = now + 10
  gv:beginFrame(true, 10.0)
  local importsBefore = farfield.stats().imports
  farfield.update(gv, DT, camSouth)
  T.check(farfield.stats().groups == 2, 'burst mode reveals at most 1 waiting swap group per frame (2 of 3 still waiting)')
  T.check(farfield.stats().imports == importsBefore, 'no tile import in a governed frame that revealed a swap group')

  -- Drain remaining reveals and import over subsequent frames (no starvation)
  gv.burst = false
  for _ = 1, 30 do
    now = now + 10
    gv:beginFrame(farfield.hasWork(), 10.0)
    farfield.update(gv, DT, camSouth)
  end
  T.check(farfield.stats().groups == 0 and farfield._pending(key(0, 20, 10)).loaded,
    'all waiting swap groups revealed and queued tile imported within 30 frames')
  farfield.switchAnchor(71, false, { cx = 0, cy = 0 })
  step(free, nil, 50)
end

T.done('test_farfield')"""

assert old1 in text, "old1 not found"
text = text.replace(old1, new1, 1)

with open(path, "wb") as f:
    f.write(text.replace("\n", nl).encode("utf-8"))
print("Updated copies/test_farfield.lua")
