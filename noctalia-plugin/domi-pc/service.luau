--!nonstrict
-- Consulta `domictl status --json` y ejecuta on/off cuando el widget lo pide.
noctalia.setUpdateInterval(5000)

local busy = false
local lastToggle = 0

local function refresh()
  if busy then return end
  noctalia.runAsync({ "domictl", "status", "--json" }, function(result)
    if result and result.exitCode == 0 then
      local s = noctalia.json.decode(result.stdout or "")
      if type(s) == "table" then
        noctalia.state.set("available", true)
        noctalia.state.set("on", s.on == true)
        noctalia.state.set("connected", s.connected == true)
        noctalia.state.set("since", s.since or 0)
        noctalia.state.set("gpu", s.gpu or "")
        return
      end
    end
    noctalia.state.set("available", false)
  end, 8000)
end

local function toggle()
  if busy then return end
  busy = true
  noctalia.state.set("busy", true)
  local turningOn = noctalia.state.get("on") ~= true
  local cmd = turningOn and { "domictl", "on" } or { "domictl", "off" }
  noctalia.runAsync(cmd, function(result)
    busy = false
    noctalia.state.set("busy", false)
    if result and result.exitCode ~= 0 then
      local msg = noctalia.string.trim(result.stderr or "")
      if msg == "" then msg = noctalia.string.trim(result.stdout or "") end
      noctalia.notifyError("Domi-PC", msg ~= "" and msg or noctalia.tr("notify.failed"))
    end
    refresh()
  end, 120000)
end

noctalia.state.watch("requestToggle", function(v)
  if v and v ~= lastToggle then
    lastToggle = v
    toggle()
  end
end)

function update() refresh() end
refresh()
