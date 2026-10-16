<div align="center">

# 🎮 domi-pc

### Tu portátil, dos personas, cero peleas por la GPU.

**Trabaja en tu escritorio mientras alguien más juega, desde donde sea, en la RTX de tu mismo equipo.**
Cuando terminan, un comando te devuelve la máquina entera, y te demuestra que no quedó nada.

[Empezar](#-instalación-en-5-minutos) · [Cómo funciona](#-cómo-funciona) · [Roadmap](ROADMAP.md) · [Contribuir](CONTRIBUTING.md) · [English](README.en.md)

`Moonlight` · `Moonshine` · `Hyprland` · `NVIDIA` · `Tailscale` · `Proton` · `MIT`

</div>

> 🩷 *Para Domi. Este proyecto existe por ella y por eso se llama así.* [Leer la historia](#-por-qué-se-llama-domi-pc)

---

## ¿Por qué existe?

Querías compartir tu PC con tu pareja, tu hermana o tu mejor amigo para que juegue **sin comprarle otro equipo**.
Las opciones de siempre fallan en lo mismo:

| Lo habitual | El problema |
|---|---|
| Steam Remote Play / Parsec sobre tu sesión | Se pisan: ella ve y toca **tu** escritorio |
| Una VM con GPU passthrough | Pierdes la GPU (y tu pantalla) mientras juega |
| Un segundo usuario "a mano" | Sin aislamiento: sus juegos pueden ver tu LAN, tu trabajo y tus archivos |
| Dejarlo corriendo "por si acaso" | Tu RAM, tu batería y tu GPU ya no son tuyas |

**domi-pc** crea una sesión de juego **aislada, con límites y con interruptor**, y la transmite por Moonlight.

## ✨ Lo que ofrece

- 🔌 **On/off real.** `domictl off` apaga todo y **verifica** procesos, GPU, red y puertos. Si algo queda, lo cierra y te avisa. Tu máquina vuelve a ser solo tuya.
- 🛡️ **Aislamiento serio.** Usuario separado sin login, firewall de salida (sin acceso a tu LAN ni a tu tailnet de trabajo), mandos virtuales solo de ella, límites de RAM, sin ver tu teclado ni tu ratón.
- 🚀 **Rendimiento de GPU dedicada.** Render y encoder fijados a la NVIDIA (NVENC). Tu escritorio sigue en la iGPU.
- 🌐 **Internet sin abrir puertos.** Una tailnet personal en un *namespace* aislado: ella se conecta desde datos móviles o desde otra ciudad.
- 🖼️ **Panel web bonito.** Biblioteca con portadas de SteamGridDB, búsqueda libre, aplicar varios assets seguidos, renombrar, ver espacio y eliminar juegos.
- 📥 **Buzón de juegos.** Suelta una carpeta o un `.zip/.7z/.rar` en `~/Juegos-Domi`: se importa, recibe portadas y aparece en su Steam.
- 🧩 **Juegos que no son de Steam.** Proton para `.exe`, launchers que se actualizan solos, y Roblox (Sober) listo para usar.
- 🧰 **Diagnóstico por capas.** `domictl doctor` te dice qué falla, dónde y cómo arreglarlo.
- 🔔 **Widget para tu barra** (Noctalia): un clic enciende/apaga y el color te dice si ella está jugando.
- 🧑‍🤝‍🧑 **Partidas LAN entre ustedes dos**, aunque estén en el mismo PC.

## 🧭 Cómo funciona

```
 Domi (cualquier dispositivo)                    Tu portátil
┌────────────────────┐   Tailscale / LAN   ┌─────────────────────────────────────────────┐
│  Moonlight         │ ◄─────────────────► │  Moonshine ──► compositor headless ──► juego │
└────────────────────┘                     │     │            (usuario `domi`, RTX 4050)  │
                                           │     └─ NVENC                                │
                                           │                                             │
                                           │  Tu Hyprland, tus apps (iGPU) ── intactos   │
                                           └─────────────────────────────────────────────┘
```

| Pieza | Qué hace |
|---|---|
| Usuario `domi` | Sesión separada (su Steam, su audio, sus flatpaks); sin login, shell `nologin` |
| Moonshine | Servidor Moonlight; compositor headless por stream; render y encoder en la NVIDIA |
| Firewall de salida | Los procesos de `domi` no alcanzan tu LAN ni otras tailnets (sí las direcciones de tu propio equipo) |
| VPN | `tailscaled` propio en un netns (`domi-ts`); solo se exponen los puertos de Moonshine |
| Input | Mandos virtuales solo de `domi` (`seat-domi`); sus juegos no pueden crear dispositivos |
| Límites | `user-<uid>.slice`: MemoryHigh 9G / MemoryMax 11G |
| Permisos | sudoers/polkit: tú actúas como `domi` y gestionas solo los servicios del modo |
| Panel web | Solo `127.0.0.1` + token aleatorio; la API key llega por stdin |

## 📦 Requisitos

Arch/CachyOS (o similar con systemd) · GPU NVIDIA con driver propietario · Hyprland u otro Wayland ·
[`moonshine-bin`](https://aur.archlinux.org/packages/moonshine-bin) · `tailscale` · `python-vdf` · `iptables` · `polkit` · `acl` · `gamescope` (para Roblox) · `notify-send` (opcional) · Noctalia 5 (opcional, widget).

## 🚀 Instalación en 5 minutos

```bash
git clone https://github.com/esteban-dcp/domi-pc && cd domi-pc
pkexec bash "$PWD/system/install-system.sh"      # ruta absoluta: pkexec no respeta el cwd
```

El instalador es **idempotente** y lo prepara todo: usuario aislado, grupos, sudoers/polkit/udev, límites de memoria,
firewall, unidades de systemd y la config de Moonshine. Escribe `/etc/domi-pc.conf` (`ADMIN_USER`, `DOMI_USER`, `NV_PCI`;
autodetecta la NVIDIA). Después:

1. Cierra sesión y vuelve a entrar (grupo `games`).
2. Autentica la tailnet de Domi (usa una cuenta **personal**, separada de la de trabajo):
   `tailscale --socket=/run/domi-tailscale/tailscaled.sock up --hostname=domi-pc`
3. *(Opcional)* API key de SteamGridDB en `~/.config/domi-pc/steamgriddb.key` para las portadas.
4. Importador de juegos: `systemctl --user enable --now domi-import.path`
5. `domictl doctor` → **«Todo en orden»**. Instala Moonlight en el dispositivo de Domi, añade el PC y `domictl pin 1234`.

## 🕹️ Uso diario

```bash
domictl on              # activa el modo (pausa Docker y JetBrains, levanta VPN + Moonshine)
domictl off [--force]   # lo apaga, restaura lo pausado y VERIFICA que no queda nada de Domi
domictl status [--json] # quién está conectada, GPU, RAM, VPN
domictl doctor          # diagnóstico por capas, con pistas de arreglo
domictl pin 1234        # emparejar un cliente Moonlight nuevo
domictl panel           # panel web: portadas, añadir/renombrar/eliminar juegos, disco
domictl sync            # reaplicar juegos no-Steam y portadas a la cuenta de Steam de Domi
domictl logs            # logs de Moonshine
```

<details>
<summary><b>Añadir juegos que no son de Steam</b></summary>

Suelta la carpeta (con su `.exe`) o un `.zip/.7z/.rar` en **`~/Juegos-Domi`**. Cuando termina de copiarse se mueve a
`/srv/juegos/`, recibe portadas y aparece en el Steam de Domi. Si falla, queda en `~/Juegos-Domi-revisar/` con un
`.motivo.txt`. Para quitar un juego y liberar espacio: `domictl panel` → **Eliminar y liberar N GB**.
</details>

<details>
<summary><b>Juegos con launcher propio (se actualizan solos)</b></summary>

Suelta la carpeta del launcher. El acceso de Steam debe apuntar al launcher, no al `.exe` del juego. Si el importador
eligió otro, corrígelo en el panel o con `domictl add-game "Nombre" /srv/juegos/<carpeta>/<launcher>.exe`.
El panel también **renombra** el juego en Steam conservando portadas y partidas.
</details>

<details>
<summary><b>Roblox</b></summary>

Funciona con Sober + gamescope en la NVIDIA. Los cuatro detalles que costó descubrir están en
[docs/roblox-sober.md](docs/roblox-sober.md).
</details>

<details>
<summary><b>Widget de Noctalia</b></summary>

```bash
ln -s "$PWD/noctalia-plugin/domi-pc" ~/.local/share/noctalia-plugins-local/domi-pc
noctalia msg plugins enable local/domi-pc
# añade "local/domi-pc:toggle" a bar.default.end en ~/.config/noctalia/config.toml
```
</details>

<details>
<summary><b>Partidas LAN entre ustedes dos</b></summary>

El firewall bloquea la LAN pero permite las direcciones del propio equipo: pueden jugar en LAN en el mismo PC
uniéndose por IP (`127.0.0.1` o la IP LAN del portátil). Los listados automáticos por broadcast no funcionan.
</details>

## 🗺️ Roadmap

Minecraft (Java con administración de instalaciones desde el panel, y Bedrock), editor de apps de Moonshine en el panel,
más launchers, horarios y límites de tiempo, respaldo de partidas y mucho más. **→ [ROADMAP.md](ROADMAP.md)**

## 🔒 Seguridad y límites honestos

Esto aísla a un usuario *de confianza* en tu máquina, no es un sandbox contra un atacante determinado.

- El firewall no bloquea `127.0.0.0/8`: los juegos de Domi llegan a servicios locales tuyos (servidores de desarrollo, por ejemplo).
- `/srv/juegos` no tiene el bit *sticky*: Domi puede borrar carpetas del administrador (el panel lo necesita para eliminar juegos).
- Coste en modo apagado: su sesión queda en *linger* (~7 MB) más reglas de firewall/udev inertes. No hay apagado automático.
- Probado en CachyOS + Hyprland + RTX 4050. En otras combinaciones, [cuéntanos](CONTRIBUTING.md#reporta-tu-hardware).

## 🤝 Contribuir

Hay un [CONTRIBUTING](CONTRIBUTING.md) con reglas de oro, una checklist de pruebas y una lista de cosas que nos encantaría ver.

## 🩷 Por qué se llama domi-pc

Este proyecto está hecho **en honor a Domi**, mi novia. Todo empezó con una idea simple: que ella pudiera jugar
en mi computador, sin que yo dejara de trabajar y sin que ninguno de los dos se estorbara. De ahí salió el usuario
`domi`, el modo Domi y el nombre `domi-pc`.

Sin ella no existiría nada de esto: fue su motivo para montarlo, y cada pieza (el aislamiento, el panel, las
portadas, el `off` que devuelve todo) está pensada para que ella juegue tranquila y yo también. Gracias, Domi. 🩷

Si te sirve para compartir tu PC con alguien que quieres, esa es la mejor razón para usarlo.

## 📄 Licencia

[MIT](LICENSE). Moonshine, Moonlight, Sober, gamescope y SteamGridDB son proyectos de sus respectivos autores.
