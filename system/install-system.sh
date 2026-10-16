#!/usr/bin/env bash
# Instala/actualiza las piezas de sistema de domi-pc.
# Ejecutar con: pkexec bash /ruta/absoluta/a/domi-pc/system/install-system.sh
# Configuración: /etc/domi-pc.conf (se genera la primera vez; editable). Variables:
#   ADMIN_USER  usuario que administra el modo Domi (por defecto, quien lanza pkexec/sudo)
#   DOMI_USER   usuario de juego aislado (por defecto: domi, debe existir)
#   NV_PCI      dirección PCI de la GPU NVIDIA (por defecto: autodetectada)
set -euo pipefail
SRC=$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)
LIB=/usr/local/lib/domi-pc
CONF=/etc/domi-pc.conf

[[ -r $CONF ]] && . "$CONF"
if [[ -z ${ADMIN_USER:-} ]]; then
  ADMIN_USER=${PKEXEC_UID:+$(id -nu "$PKEXEC_UID")}
  ADMIN_USER=${ADMIN_USER:-${SUDO_USER:-}}
fi
DOMI_USER=${DOMI_USER:-domi}
if [[ -z ${NV_PCI:-} ]]; then
  for d in /sys/class/drm/renderD*/device; do
    [[ $(cat "$d/vendor" 2>/dev/null) == 0x10de ]] && { NV_PCI=$(basename "$(readlink -f "$d")"); break; }
  done
fi
[[ -n $ADMIN_USER ]] || { echo "No pude determinar ADMIN_USER (defínelo en $CONF)"; exit 1; }
[[ -n ${NV_PCI:-} ]] || { echo "No encontré GPU NVIDIA (defínela como NV_PCI en $CONF)"; exit 1; }

for c in moonshine tailscale tailscaled setfacl iptables nvidia-smi; do
  command -v "$c" >/dev/null || { echo "Falta la dependencia: $c (ver README, Requisitos)"; exit 1; }
done
re='^[a-z_][a-z0-9_-]*$'
[[ $ADMIN_USER =~ $re && $DOMI_USER =~ $re ]] || { echo "ADMIN_USER/DOMI_USER inválidos (solo [a-z0-9_-])"; exit 1; }
[[ $ADMIN_USER != root && $ADMIN_USER != "$DOMI_USER" ]] || { echo "ADMIN_USER no puede ser root ni igual a DOMI_USER"; exit 1; }
[[ $NV_PCI =~ ^[0-9a-f:.]+$ ]] || { echo "NV_PCI inválido"; exit 1; }

echo "== base: usuario, grupos, sudoers, juegos"
getent group games >/dev/null || groupadd games
getent group moonshine >/dev/null || groupadd -r moonshine
if ! id "$DOMI_USER" &>/dev/null; then
  useradd -m -U -s /usr/bin/nologin -G video,render,games "$DOMI_USER"
fi
usermod -aG video,render,games "$DOMI_USER"
passwd -l "$DOMI_USER" >/dev/null                      # sin login por contraseña
usermod -aG "$DOMI_USER",games "$ADMIN_USER"           # el admin gestiona el HOME de domi
DOMI_HOME=$(getent passwd "$DOMI_USER" | cut -d: -f6)
chmod 2770 "$DOMI_HOME"
loginctl enable-linger "$DOMI_USER"
install -d -m2775 -g games /srv/juegos
tmp=$(mktemp); printf '%s ALL=(%s) NOPASSWD: ALL\n' "$ADMIN_USER" "$DOMI_USER" > "$tmp"
visudo -cf "$tmp" >/dev/null && install -m440 "$tmp" /etc/sudoers.d/50-domi-pc; rm -f "$tmp"
modprobe uhid || true
DOMI_UID=$(id -u "$DOMI_USER")
ADMIN_HOME=$(getent passwd "$ADMIN_USER" | cut -d: -f6)
printf 'ADMIN_USER=%s\nDOMI_USER=%s\nNV_PCI=%s\n' "$ADMIN_USER" "$DOMI_USER" "$NV_PCI" > "$CONF"
chmod 644 "$CONF"
echo "== admin=$ADMIN_USER domi=$DOMI_USER (uid $DOMI_UID) gpu=$NV_PCI"

render() { sed -e "s|@ADMIN@|$ADMIN_USER|g" -e "s|@DOMI@|$DOMI_USER|g" -e "s|@NV_PCI@|$NV_PCI|g" "$1"; }
install_t() { install -d "$(dirname "$2")"; render "$1" > "$2"; chmod 644 "$2"; }  # plantilla -> destino

TS="ip netns exec domi-ts tailscale --socket=/run/domi-tailscale/tailscaled.sock"

echo "== scripts en $LIB (root:root, fuera del HOME del admin)"
install -d -m755 "$LIB"
install -m755 "$SRC/system/domi-netns.sh" "$SRC/system/domi-firewall.sh" "$SRC/bin/domi-import" "$LIB/"
install -m755 "$SRC/bin/domictl" /usr/local/bin/domictl
(cd "$SRC/scripts" && install -m644 steamshortcuts.py sgdb.py domi-panel.py domi-add-game.py domi-sync.py domi-register.py "$LIB/")
install -d -m755 "$LIB/panel"
install -m644 "$SRC"/scripts/panel/* "$LIB/panel/"

echo "== unidades, polkit, udev, límites"
install -Dm644 "$SRC/system/domi-tailscale.service" "/etc/systemd/system/domi-tailscale.service"
install_t "$SRC/system/domi-firewall.service" "/etc/systemd/system/domi-firewall.service"
install -Dm644 "$SRC/system/user-slice.conf" "/etc/systemd/system/user-$DOMI_UID.slice.d/50-domi-pc.conf"
install -Dm644 "$SRC/system/user/domi-import.service" "/etc/systemd/user/domi-import.service"
install -Dm644 "$SRC/system/user/domi-import.path" "/etc/systemd/user/domi-import.path"
install_t "$SRC/system/50-domi-pc.rules" "/etc/polkit-1/rules.d/50-domi-pc.rules"
install_t "$SRC/system/moonshine-domi-dropin.conf" "/etc/systemd/system/moonshine@$DOMI_USER.service.d/10-domi-pc.conf"
install_t "$SRC/system/61-domi-pc-input.rules" "/etc/udev/rules.d/61-domi-pc-input.rules"
udevadm control --reload
udevadm trigger --subsystem-match=misc --subsystem-match=input --subsystem-match=hidraw || true

echo "== $DOMI_USER fuera del grupo moonshine"
NEED_USER_RESTART=0
if id -nG "$DOMI_USER" | grep -qw moonshine; then gpasswd -d "$DOMI_USER" moonshine; NEED_USER_RESTART=1; fi

echo "== quitar ACL de $DOMI_USER sobre el HOME del admin"
setfacl -x "u:$DOMI_USER" "$ADMIN_HOME" "$(dirname "$SRC")" "$SRC" 2>/dev/null || true
setfacl -R -x "u:$DOMI_USER" "$SRC/scripts" 2>/dev/null || true
setfacl -k "$SRC/scripts" 2>/dev/null || true
rm -f "$DOMI_HOME/.config/domi-pc/sgdb.key"

echo "== configuración de Moonshine (solo si no existe)"
MCONF="$DOMI_HOME/.config/moonshine"
if [[ ! -e $MCONF/config.toml ]]; then
  sudo -u "$DOMI_USER" install -d -m700 "$MCONF" "$MCONF/boxart"
  render "$SRC/system/moonshine-config.example.toml" | sudo -u "$DOMI_USER" tee "$MCONF/config.toml" >/dev/null
  echo "   creado $MCONF/config.toml (revisa teclado y apps)"
fi
sudo -u "$DOMI_USER" install -m644 "$SRC/system/boxart/dev.png" "$MCONF/boxart/dev.png" 2>/dev/null || true

# Un panel abierto antes de reinstalar seguiría con el código viejo: se cierra (se reabre con `domictl panel`)
pkill -u "$DOMI_USER" -f 'domi-panel.py' 2>/dev/null && echo "== panel de Domi cerrado: vuelve a abrirlo con domictl panel" || true

systemctl daemon-reload
systemctl enable --now domi-firewall.service
if systemctl is-active -q domi-tailscale.service; then
  $LIB/domi-netns.sh up
  # tailscaled de Domi sin reglas propias (las gestionamos nosotros) y sin operador
  $TS up --netfilter-mode=off --accept-dns=false --hostname=domi-pc --operator= 2>&1 | tail -2 || true
fi

if (( NEED_USER_RESTART )); then
  echo "== reiniciar la sesión de $DOMI_USER para que pierda el grupo moonshine"
  systemctl stop "moonshine@$DOMI_USER.service" 2>/dev/null || true
  systemctl restart "user@$DOMI_UID.service"
fi
echo "== OK"
id "$DOMI_USER"
