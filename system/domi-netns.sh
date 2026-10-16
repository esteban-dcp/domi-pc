#!/usr/bin/env bash
# Red aislada para la VPN de Domi.
#
# Un network namespace "domi-ts" con su propio tailscaled, conectado a la
# tailnet personal. Solo se reenvían al host los puertos de Moonshine, así que
# los peers de esa tailnet no ven nada más del portátil. La tailnet de trabajo
# (tailscale0 del host) no se toca.
#
#   host (10.77.0.1/30) veth-domi-h <──> veth-domi-n (10.77.0.2/30) [ns domi-ts] tailscale0
#
# Uso: domi-netns.sh up|down
set -euo pipefail

NS=domi-ts
VH=veth-domi-h
VN=veth-domi-n
HOST_IP=10.77.0.1
NS_IP=10.77.0.2
NET=10.77.0.0/30
TCP_PORTS=47984,47989,48010
UDP_PORTS=47998:48010
TS_PORT=41642

ipt() { iptables -w "$@"; }
nsipt() { ip netns exec "$NS" iptables -w "$@"; }
# Cadena propia (creada vacía) y salto idempotente al principio de la cadena base
chain() { ipt -t "$1" -N "$2" 2>/dev/null || ipt -t "$1" -F "$2"; }
jump() { local t=$1 base=$2; shift 2; ipt -t "$t" -C "$base" "$@" 2>/dev/null || ipt -t "$t" -I "$base" "$@"; }
unjump() { local t=$1 base=$2; shift 2; while ipt -t "$t" -D "$base" "$@" 2>/dev/null; do :; done; }

up() {
  [[ -e /run/netns/$NS ]] || ip netns add "$NS"
  if ! ip link show "$VH" &>/dev/null; then
    ip link add "$VH" type veth peer name "$VN"
    ip link set "$VN" netns "$NS"
  fi
  ip addr replace "$HOST_IP/30" dev "$VH"
  ip link set "$VH" up
  ip netns exec "$NS" ip addr replace "$NS_IP/30" dev "$VN"
  ip netns exec "$NS" ip link set "$VN" up
  ip netns exec "$NS" ip link set lo up
  ip netns exec "$NS" ip route replace default via "$HOST_IP"
  ip netns exec "$NS" sysctl -qw net.ipv4.ip_forward=1

  # DNS propio del namespace (ip netns exec monta /etc/netns/$NS/resolv.conf)
  mkdir -p "/etc/netns/$NS"
  printf 'nameserver 1.1.1.1\nnameserver 9.9.9.9\n' > "/etc/netns/$NS/resolv.conf"

  # Host: reenvío IPv4 propio (antes dependía de que Docker lo activara)
  sysctl -qw net.ipv4.ip_forward=1

  # Host: salida a internet del namespace
  ipt -t nat -C POSTROUTING -s "$NET" ! -o "$VH" -j MASQUERADE 2>/dev/null ||
    ipt -t nat -A POSTROUTING -s "$NET" ! -o "$VH" -j MASQUERADE

  # Host: desde la veth solo se acepta Moonshine (ufw permite otros puertos a cualquiera)
  chain filter DOMI-VETH-IN
  ipt -A DOMI-VETH-IN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  ipt -A DOMI-VETH-IN -p tcp -m multiport --dports "$TCP_PORTS" -j ACCEPT
  ipt -A DOMI-VETH-IN -p udp --dport "$UDP_PORTS" -j ACCEPT
  ipt -A DOMI-VETH-IN -j DROP
  jump filter INPUT -i "$VH" -j DOMI-VETH-IN

  # Host: reenvío. El namespace sale a internet, nunca a la LAN, Docker ni la tailnet de trabajo.
  chain filter DOMI-FWD
  ipt -A DOMI-FWD -o "$VH" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  ipt -A DOMI-FWD -o "$VH" -p udp -d "$NS_IP" --dport "$TS_PORT" -j ACCEPT
  ipt -A DOMI-FWD -o "$VH" -j DROP
  for net in 100.64.0.0/10 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16; do
    ipt -A DOMI-FWD -i "$VH" -d "$net" -j DROP
  done
  ipt -A DOMI-FWD -i "$VH" -o tailscale0 -j DROP
  ipt -A DOMI-FWD -i "$VH" -j ACCEPT
  jump filter FORWARD -j DOMI-FWD

  # Host: el puerto WireGuard de la tailnet de Domi (UDP $TS_PORT) que llega a este host
  # desde fuera entra al namespace (peers tras NAT estricto conectan directo y no por DERP).
  chain nat DOMI-PRE
  ipt -t nat -A DOMI-PRE -i "$VH" -j RETURN
  ipt -t nat -A DOMI-PRE -i tailscale0 -j RETURN
  ipt -t nat -A DOMI-PRE -i docker0 -j RETURN
  ipt -t nat -A DOMI-PRE -i br-+ -j RETURN
  ipt -t nat -A DOMI-PRE -p udp --dport "$TS_PORT" -m addrtype --dst-type LOCAL -j DNAT --to-destination "$NS_IP:$TS_PORT"
  jump nat PREROUTING -j DOMI-PRE

  # Namespace: lo que entra por la tailnet a puertos de Moonshine va al host
  nsipt -t nat -F
  nsipt -F FORWARD
  nsipt -P FORWARD DROP
  nsipt -t nat -A PREROUTING -i tailscale0 -p tcp -m multiport --dports "$TCP_PORTS" -j DNAT --to-destination "$HOST_IP"
  nsipt -t nat -A PREROUTING -i tailscale0 -p udp --dport "$UDP_PORTS" -j DNAT --to-destination "$HOST_IP"
  nsipt -t nat -A POSTROUTING -o "$VN" -d "$HOST_IP" -j MASQUERADE
  nsipt -A FORWARD -i tailscale0 -o "$VN" -d "$HOST_IP" -p tcp -m multiport --dports "$TCP_PORTS" -j ACCEPT
  nsipt -A FORWARD -i tailscale0 -o "$VN" -d "$HOST_IP" -p udp --dport "$UDP_PORTS" -j ACCEPT
  nsipt -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
}

down() {
  unjump filter INPUT -i "$VH" -j DOMI-VETH-IN
  unjump filter FORWARD -j DOMI-FWD
  unjump nat PREROUTING -j DOMI-PRE
  for c in "filter DOMI-VETH-IN" "filter DOMI-FWD" "nat DOMI-PRE"; do
    set -- $c
    ipt -t "$1" -F "$2" 2>/dev/null || true
    ipt -t "$1" -X "$2" 2>/dev/null || true
  done
  ipt -t nat -D POSTROUTING -s "$NET" ! -o "$VH" -j MASQUERADE 2>/dev/null || true
  ip link del "$VH" 2>/dev/null || true
  ip netns del "$NS" 2>/dev/null || true
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *) echo "uso: $0 up|down" >&2; exit 1 ;;
esac
