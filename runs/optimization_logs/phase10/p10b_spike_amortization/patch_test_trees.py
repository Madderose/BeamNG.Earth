path = "runs/optimization_logs/phase10/p10b_spike_amortization/copies/test_trees.lua"
with open(path, "rb") as f:
    raw = f.read()

has_crlf = b"\r\n" in raw
nl = "\r\n" if has_crlf else "\n"
text = raw.decode("utf-8").replace("\r\n", "\n")

old1 = """T.check(reused, 'a pooled Forest is reset to no transform when reused')
trees.clear()
T.done('test_trees')"""

new1 = """T.check(reused, 'a pooled Forest is reset to no transform when reused')
trees.clear()

-- P10-B: distinct-Forest mutation cap (MAX_FORESTS_PER_FRAME = 2 in governed mode, 1 in burst mode)
-- and rotation / no starvation across 4 pending tiles
do
  local governor = require('beamngEarth/governor')
  local gTime = 0
  local gv = governor.new({ clock = function() return gTime end })
  for _ = 1, 80 do gTime = gTime + 10; gv:beginFrame(true, 10.0) end
  for ti = 0, 3 do
    local k = ti .. '_0'
    local r = {}
    for i = 0, 7 do r[#r + 1] = string.format('{0, %d, 10, 5, 0, 1, 12, %.3f}', i, i / 16) end
    files['/t/f_' .. k] = '{ groups = {}, items = { ' .. table.concat(r, ', ') .. ' } }'
    trees.onTile({ anchorId = 11, key = k, path = '/t/f_' .. k, n = 8 }, 11)
  end
  -- Frame 1 (governed, normal): at most MAX_FORESTS_PER_FRAME (2) distinct Forests touched
  gTime = gTime + 10
  gv:beginFrame(true, 10.0)
  trees.update(11, { x = 128, y = 128 }, nil, gv)
  T.check((trees.lastForestsTouched or 0) <= trees.MAX_FORESTS_PER_FRAME,
    'governed update touches at most MAX_FORESTS_PER_FRAME Forests (' .. tostring(trees.lastForestsTouched) .. ')')
  T.check(count() > 0 and count() <= 16, 'first governed frame fills at most 2 tiles of 8 items (' .. count() .. ')')

  -- Burst mode: at most 1 distinct Forest touched per frame
  gv.burst = true
  local maxBurstForests = 0
  for _ = 1, 20 do
    gTime = gTime + 10
    gv:beginFrame(true, 10.0)
    trees.update(11, { x = 128, y = 128 }, nil, gv)
    if (trees.lastForestsTouched or 0) > maxBurstForests then
      maxBurstForests = trees.lastForestsTouched
    end
    if count() == 32 then break end
  end
  T.check(maxBurstForests <= 1, 'burst mode touches at most 1 Forest per frame (' .. maxBurstForests .. ')')
  T.check(count() == 32 and trees.status().pending == 0, 'all 4 tiles complete without starvation (' .. count() .. ')')
  trees.clear()
end
T.done('test_trees')"""

assert old1 in text, "old1 not found"
text = text.replace(old1, new1, 1)

with open(path, "wb") as f:
    f.write(text.replace("\n", nl).encode("utf-8"))
print("Updated copies/test_trees.lua")
