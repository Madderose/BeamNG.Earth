path = "runs/optimization_logs/phase10/p10b_spike_amortization/copies/farfield.lua"
with open(path, "rb") as f:
    raw = f.read()

has_crlf = b"\r\n" in raw
nl = "\r\n" if has_crlf else "\n"
text = raw.decode("utf-8").replace("\r\n", "\n")

old1 = """M.EXACT_OFF = 0.01      -- m; an exact tile further than this off its height (crossover) is a miss
M.RETEX_PER_FRAME = 2   -- far_retex material switches per frame at most (each also a governor unit)"""

new1 = """M.EXACT_OFF = 0.01      -- m; an exact tile further than this off its height (crossover) is a miss
M.RETEX_PER_FRAME = 2   -- far_retex material switches per frame at most (each also a governor unit)
M.REVEALS_PER_FRAME = 2 -- swap groups revealed per frame at most during governed streaming (1 in burst mode)"""

assert old1 in text, "old1 not found"
text = text.replace(old1, new1, 1)

old2 = """  local stop = false
  for _, g in ipairs(groups) do
    if g.state == 'wait' then
      local blocked = stop or frozen
      if not blocked then
        for _, k in ipairs(g.add) do if busy[k] then blocked = true; break end end
      end
      if not blocked then
        for _, k in ipairs(g.remove) do if busy[k] then blocked = true; break end end
      end
      if not blocked and groupReady(g) then
        if gov:try('reveal') then
          local t1 = now()
          if startGroup(g, cam, player) then
            gov:charge('reveal', now() - t1)
            units = units + 1
          end -- else: waits for a crossover slot; its keys stay busy, other groups go on
        else
          stop = true -- out of budget: keep the order, try again next frame
        end
      end"""

new2 = """  local stop = false
  local nRevealed = 0
  local maxReveals = (gov.frame == nil or gov.loading) and huge or ((gov.burst and 1) or M.REVEALS_PER_FRAME or 2)
  for _, g in ipairs(groups) do
    if g.state == 'wait' then
      local blocked = stop or frozen or (nRevealed >= maxReveals)
      if not blocked then
        for _, k in ipairs(g.add) do if busy[k] then blocked = true; break end end
      end
      if not blocked then
        for _, k in ipairs(g.remove) do if busy[k] then blocked = true; break end end
      end
      if not blocked and groupReady(g) then
        if gov:try('reveal') then
          local t1 = now()
          if startGroup(g, cam, player) then
            gov:charge('reveal', now() - t1)
            units = units + 1
            nRevealed = nRevealed + 1
            if nRevealed >= maxReveals then stop = true end
          end -- else: waits for a crossover slot; its keys stay busy, other groups go on
        else
          stop = true -- out of budget: keep the order, try again next frame
        end
      end"""

assert old2 in text, "old2 not found"
text = text.replace(old2, new2, 1)

old3 = """  -- 4. imports (hidden), group tiles first, prefetch only when nothing else waits. A tile with its
  --    own imagery material gets the Material first, as a separate unit (satmat.lua); a re-sent key
  --    or a sibling sharing the name re-uses it for free.
  local imported = false
  while true do"""

new3 = """  -- 4. imports (hidden), group tiles first, prefetch only when nothing else waits. A tile with its
  --    own imagery material gets the Material first, as a separate unit (satmat.lua); a re-sent key
  --    or a sibling sharing the name re-uses it for free.
  --    Yield imports on frames that already revealed a swap group (unless loading or free test gov) so
  --    unhide + .cdae resource init never stack in the same frame's RenderShadows pass.
  local imported = false
  local allowImports = (gov.frame == nil or gov.loading or nRevealed == 0)
  while allowImports do"""

assert old3 in text, "old3 not found"
text = text.replace(old3, new3, 1)

old4 = """  -- 4b. far_retex: material texture switches, a few per frame within the budget (never thrown out of
  --     the frame: a failing switch is counted and dropped)
  local nRetex = 0
  while nRetex < M.RETEX_PER_FRAME and satmat.hasRetex() and gov:try('retex') do"""

new4 = """  -- 4b. far_retex: material texture switches, a few per frame within the budget (never thrown out of
  --     the frame: a failing switch is counted and dropped). Yield when an import or reveal already ran.
  local nRetex = 0
  while (not imported and nRevealed == 0) and nRetex < M.RETEX_PER_FRAME and satmat.hasRetex() and gov:try('retex') do"""

assert old4 in text, "old4 not found"
text = text.replace(old4, new4, 1)

with open(path, "wb") as f:
    f.write(text.replace("\n", nl).encode("utf-8"))
print("Successfully updated copies/farfield.lua")
