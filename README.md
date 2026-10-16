# domi-pc

Un portátil Linux, dos personas: tú sigues trabajando en tu escritorio (Hyprland) mientras otra persona
juega por internet en la **GPU NVIDIA** del mismo equipo, en una sesión aislada, transmitida con
[Moonshine](https://github.com/hgaiser/moonshine) (servidor Moonlight). Cuando terminas, `domictl off`
devuelve la máquina entera a tu sesión y verifica que no queda nada.

*A Linux laptop, two people: you keep working on your desktop while someone else plays remotely on the
same machine's NVIDIA GPU, in an isolated session streamed with Moonshine (Moonlight protocol).
`domictl off` gives the whole machine back and verifies nothing is left behind.*

## Requisitos

Arch/CachyOS (o similar con systemd), GPU NVIDIA con driver propietario, Hyprland u otro compositor Wayland,
[`moonshine-bin`](https://aur.archlinux.org/packages/moonshine-bin), `tailscale`, `python-vdf`,
`iptables`, `polkit`, `acl`, `zenity`/`notify-send` (opcional). Opcional: Noctalia 5 para el widget de barra.

## Instalación

```
git clone <este-repo> && cd domi-pc
pkexec bash "$PWD/system/install-system.sh"      # ruta absoluta (pkexec no respeta cwd)
```

El instalador (idempotente) crea el usuario aislado `domi`, grupos, sudoers/polkit/udev, límites de memoria,
firewall de salida y unidades de systemd, y escribe `/etc/domi-pc.conf` con `ADMIN_USER`, `DOMI_USER` y
`NV_PCI` (autodetecta la NVIDIA; edítalo si hace falta). Después:

1. Cierra sesión y vuelve a entrar (grupo `games`).
2. Configura Moonshine para `domi` (`/home/domi/.config/moonshine/config.toml`) y autentica la tailnet de Domi:
   `tailscale --socket=/run/domi-tailscale/tailscaled.sock up --hostname=domi-pc`
   (usa una tailnet **personal**, separada de la de trabajo).
3. API key de SteamGridDB (opcional, portadas) en `~/.config/domi-pc/steamgriddb.key`.
4. Importador de juegos: `systemctl --user enable --now domi-import.path`.
5. `domictl doctor` debe terminar en «Todo en orden».

## Configuración de Moonshine

El instalador crea `~domi/.config/moonshine/config.toml` a partir de
[`system/moonshine-config.example.toml`](system/moonshine-config.example.toml) si no existe (apps: Steam,
Roblox con gamescope y una terminal de depuración marcada "NO TOCAR"). Puedes poner portadas 600x900 a cada
app con `boxart = "..."`. Roblox: ver [docs/roblox-sober.md](docs/roblox-sober.md).

## Uso diario

```
domictl on              # activa el modo (pausa Docker y JetBrains, levanta VPN + Moonshine)
domictl off [--force]   # lo desactiva, restaura lo pausado y VERIFICA que no queda nada de Domi
domictl status [--json] # quién está conectado, GPU, RAM, VPN
domictl doctor          # diagnóstico por capas, con pistas de arreglo
domictl pin 1234        # emparejar un cliente Moonlight nuevo
domictl panel           # panel web local: portadas (SteamGridDB), añadir/eliminar juegos, disco
domictl sync            # reaplicar juegos no-Steam + portadas a la cuenta de Steam de Domi
domictl logs            # logs de Moonshine
```

### Añadir un juego no-Steam

Suelta la carpeta (con su `.exe`) o un `.zip/.7z/.rar` en **`~/Juegos-Domi`**. Cuando termina de copiarse se
mueve a `/srv/juegos/`, recibe portadas y aparece en el Steam de Domi. Si falla, queda en
`~/Juegos-Domi-revisar/` con un `.motivo.txt`.

### Quitar un juego / liberar espacio

`domictl panel` → elegir el juego → **Eliminar y liberar N GB**. Requiere el Steam de Domi cerrado.

### Juegos con launcher propio

Si un juego trae su launcher (se actualiza solo), suelta la carpeta del launcher: el acceso de Steam debe
apuntar al launcher, no al `.exe` del juego. Si el importador eligió otro, corrígelo en `domictl panel` o con
`domictl add-game "Nombre" /srv/juegos/<carpeta>/<launcher>.exe`. El panel también permite **renombrar** el
juego en Steam (conserva portadas y partidas) y buscar portadas en SteamGridDB con cualquier nombre.

### Partidas LAN entre el administrador y Domi

El firewall de Domi bloquea la LAN, pero permite las direcciones del propio equipo: pueden jugar en LAN en
el mismo PC uniéndose por IP (`127.0.0.1` o la IP LAN del portátil). Los listados automáticos por broadcast
no funcionan.

### Widget de Noctalia

`noctalia-plugin/domi-pc/` es un plugin de barra (icono de mando; clic = on/off; color según estado).

```
ln -s "$PWD/noctalia-plugin/domi-pc" ~/.local/share/noctalia-plugins-local/domi-pc
noctalia msg plugins enable local/domi-pc
# y añade "local/domi-pc:toggle" a bar.default.end en ~/.config/noctalia/config.toml
```

## Modelo de seguridad

| Pieza | Qué hace |
|---|---|
| Usuario `domi` | Sesión separada (su Steam, PipeWire, flatpaks); sin login, shell `nologin` |
| Moonshine | Compositor headless por stream; render y encoder fijados a la NVIDIA |
| Firewall de salida | Los procesos de `domi` no alcanzan la LAN ni otras tailnets |
| VPN | `tailscaled` propio en un netns (`domi-ts`); solo se exponen los puertos de Moonshine |
| Input | Mandos virtuales solo de `domi` (`seat-domi`); sus juegos no pueden crear dispositivos |
| Límites | `user-<uid>.slice`: MemoryHigh 9G / MemoryMax 11G |
| Permisos | sudoers/polkit: el admin actúa como `domi` y gestiona sólo los servicios del modo |
| Panel web | Solo 127.0.0.1 + token aleatorio; la API key llega por stdin |

Limitaciones conocidas: el firewall no bloquea `127.0.0.0/8` (los juegos de Domi llegan a servicios locales
del administrador) y `/srv/juegos` no tiene el bit sticky (Domi puede borrar carpetas del administrador:
lo necesita el panel para eliminar juegos).

Coste en modo off: la sesión de `domi` queda en *linger* (~7 MB), más reglas de firewall/udev inertes.
No hay apagado automático: el modo se apaga a mano.

## Estructura

`bin/` (`domictl`, `domi-import`) · `scripts/` (panel web y registro de juegos, corren como `domi`) ·
`system/` (unidades, polkit, udev, firewall, config de ejemplo de Moonshine; plantillas con `@ADMIN@ @DOMI@ @NV_PCI@`) ·
`docs/` (notas, p. ej. Roblox) ·
`noctalia-plugin/` (widget).

## Licencia

MIT
