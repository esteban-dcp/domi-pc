--!nonstrict
-- Botón de barra: gamepad. Gris = apagado, primario = activo, acento = Domi conectada.
local function render()
  local available = noctalia.state.get("available") ~= false
  local on = noctalia.state.get("on") == true
  local connected = noctalia.state.get("connected") == true
  local busy = noctalia.state.get("busy") == true

  local color, tip
  if not available then
    color, tip = "on_surface_variant", noctalia.tr("tooltip.unavailable")
  elseif busy then
    color, tip = "secondary", noctalia.tr("tooltip.busy")
  elseif connected then
    color, tip = "tertiary", noctalia.tr("tooltip.connected")
  elseif on then
    color, tip = "primary", noctalia.tr("tooltip.on")
  else
    color, tip = "on_surface_variant", noctalia.tr("tooltip.off")
  end
  barWidget.setGlyph(on and "device-gamepad-2" or "device-gamepad-off")
  barWidget.setColor(color)
  barWidget.setGlyphColor(color)
  barWidget.setTooltip(tip)
end

function onClick()
  noctalia.state.set("requestToggle", noctalia.nowMs())
end

for _, k in ipairs({ "available", "on", "connected", "busy" }) do
  noctalia.state.watch(k, function(_) render() end)
end
render()
