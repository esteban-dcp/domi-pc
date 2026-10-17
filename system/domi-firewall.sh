#!/usr/bin/env bash
# Firewall de salida del usuario domi (siempre activo, no solo en modo Domi).
#
# Los juegos de Domi corren en la red del host. Esto impide que inicien conexiones hacia:
#   - la tailnet de trabajo del administrador (tailscale0, 100.64.0.0/10, fd7a:115c:a1e0::/48)
#   - la LAN y redes privadas (Docker incluido), salvo las direcciones del propio equipo
#     y el servicio de Moonshine (system.slice), que necesita hablar con su cliente
# Las respuestas a conexiones entrantes (Moonlight -> Moonshine) siguen funcionando, y la red
# aislada de la VPN de Domi (10.77.0.0/30) se permite.
#
# Uso: domi-firewall.sh up|down
set -euo pipefail

[[ -r /etc/domi-pc.conf ]] && . /etc/domi-pc.conf
DOMI=${DOMI_USER:-domi}
CHAIN=DOMI-OUT
VPN_NET=10.77.0.0/30

rules4() {
  iptables -w -N "$CHAIN" 2>/dev/null || iptables -w -F "$CHAIN"
  iptables -w -A "$CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
  iptables -w -A "$CHAIN" -d "$VPN_NET" -j RETURN
  # El servicio de Moonshine (system.slice) debe poder escribir a su cliente Moonlight, también en la LAN.
  # Los juegos de Domi viven en user.slice, así que siguen bloqueados.
  iptables -w -A "$CHAIN" -m cgroup --path system.slice -j RETURN
  # Direcciones del propio equipo (IP LAN incluida): permite partidas LAN entre el admin y Domi en el mismo PC
  iptables -w -A "$CHAIN" -m addrtype --dst-type LOCAL -j RETURN
  iptables -w -A "$CHAIN" -o tailscale0 -j REJECT
  for net in 100.64.0.0/10 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16; do
    iptables -w -A "$CHAIN" -d "$net" -j REJECT
  done
  iptables -w -C OUTPUT -m owner --uid-owner "$DOMI" -j "$CHAIN" 2>/dev/null ||
    iptables -w -I OUTPUT -m owner --uid-owner "$DOMI" -j "$CHAIN"
}

rules6() {
  ip6tables -w -N "$CHAIN" 2>/dev/null || ip6tables -w -F "$CHAIN"
  ip6tables -w -A "$CHAIN" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
  ip6tables -w -A "$CHAIN" -m cgroup --path system.slice -j RETURN
  ip6tables -w -A "$CHAIN" -m addrtype --dst-type LOCAL -j RETURN
  ip6tables -w -A "$CHAIN" -o tailscale0 -j REJECT
  for net in fd7a:115c:a1e0::/48 fc00::/7 fe80::/10; do
    ip6tables -w -A "$CHAIN" -d "$net" -j REJECT
  done
  ip6tables -w -C OUTPUT -m owner --uid-owner "$DOMI" -j "$CHAIN" 2>/dev/null ||
    ip6tables -w -I OUTPUT -m owner --uid-owner "$DOMI" -j "$CHAIN"
}

down() {
  for ipt in iptables ip6tables; do
    $ipt -w -D OUTPUT -m owner --uid-owner "$DOMI" -j "$CHAIN" 2>/dev/null || true
    $ipt -w -F "$CHAIN" 2>/dev/null || true
    $ipt -w -X "$CHAIN" 2>/dev/null || true
  done
}

case "${1:-}" in
  up) rules4; rules6 ;;
  down) down ;;
  *) echo "uso: $0 up|down" >&2; exit 1 ;;
esac
