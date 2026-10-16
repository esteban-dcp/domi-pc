<div align="center">

# 🎮 domi-pc

### Your laptop, two people, zero fights over the GPU.

**Keep working on your desktop while someone else plays from anywhere, on your own machine's NVIDIA GPU.**
When they're done, one command gives you the whole machine back, and proves nothing was left behind.

[Español](README.md) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md)

`Moonlight` · `Moonshine` · `Hyprland` · `NVIDIA` · `Tailscale` · `Proton` · `MIT`

</div>

> 💛 *For Domi. This project exists because of her, and that's why it's named after her.* [Read the story](#-why-its-called-domi-pc)

---

## Why

You wanted to share your PC with a partner, sibling or best friend so they can play **without buying them hardware**.
The usual options all fail the same way: Remote Play/Parsec on your session (they see and touch *your* desktop),
a GPU-passthrough VM (you lose the GPU while they play), a second user with no isolation (their games can reach
your LAN, your work and your files), or leaving it running "just in case" (your RAM, battery and GPU aren't yours anymore).

**domi-pc** builds a **isolated, resource-limited game session with an off switch** and streams it over Moonlight.

## Features

- 🔌 **A real on/off.** `domictl off` shuts everything down and **verifies** processes, GPU, network and ports. Anything left behind is killed and reported.
- 🛡️ **Serious isolation.** Separate login-less user, outbound firewall (no access to your LAN or work tailnet), virtual gamepads owned by the guest only, memory limits, no access to your keyboard/mouse.
- 🚀 **Dedicated-GPU performance.** Render and encoder pinned to the NVIDIA GPU (NVENC); your desktop stays on the iGPU.
- 🌐 **Internet without opening ports.** A personal tailnet in an isolated network namespace.
- 🖼️ **Web panel.** Cover art from SteamGridDB, free-text search, apply several assets in a row, rename, disk usage, delete games.
- 📥 **Drop-folder import.** Put a game folder or `.zip/.7z/.rar` in `~/Juegos-Domi`: it's imported, gets artwork and shows up in their Steam.
- 🧩 **Non-Steam games.** Proton for `.exe` files, self-updating launchers, and Roblox (Sober) ready to go.
- 🧰 **Layered diagnostics.** `domictl doctor` tells you what's wrong, where, and how to fix it.
- 🔔 **Status bar widget** (Noctalia) and LAN games between the two of you, even on the same PC.

## Requirements

Arch/CachyOS (or any systemd distro) · NVIDIA GPU + proprietary driver · Hyprland or another Wayland compositor ·
[`moonshine-bin`](https://aur.archlinux.org/packages/moonshine-bin) · `tailscale` · `python-vdf` · `iptables` · `polkit` · `acl` · `gamescope` (Roblox).

## Install

```bash
git clone https://github.com/esteban-dcp/domi-pc && cd domi-pc
pkexec bash "$PWD/system/install-system.sh"      # absolute path: pkexec ignores the cwd
```

The installer is **idempotent**: it creates the isolated user, groups, sudoers/polkit/udev rules, memory limits,
firewall, systemd units and the Moonshine config, and writes `/etc/domi-pc.conf` (`ADMIN_USER`, `DOMI_USER`,
`NV_PCI`, auto-detected). Then: log out and back in, authenticate the guest's tailnet
(`tailscale --socket=/run/domi-tailscale/tailscaled.sock up --hostname=domi-pc`, use a *personal* account),
optionally add a SteamGridDB key to `~/.config/domi-pc/steamgriddb.key`, enable the importer
(`systemctl --user enable --now domi-import.path`), run `domictl doctor`, add the PC in Moonlight and `domictl pin 1234`.

## Daily use

```bash
domictl on | off [--force] | status [--json] | doctor | pin <PIN> | panel | sync | logs
```

See the Spanish [README](README.md) for details on non-Steam games, launchers, Roblox and the Noctalia widget
(Spanish docs for now; an English translation is on the [roadmap](ROADMAP.md) and a great first contribution).

## Honest limits

This isolates a *trusted* user on your machine; it is not a sandbox against a determined attacker.
The firewall does not block `127.0.0.0/8`; `/srv/juegos` has no sticky bit (the panel needs the guest to delete games).
Tested on CachyOS + Hyprland + RTX 4050 only: [tell us about your hardware](CONTRIBUTING.md).

## 💛 Why it's called domi-pc

This project is made **in honor of Domi**, my girlfriend. It started with a simple idea: let her play on my
computer without me having to stop working and without either of us getting in the other's way. That became the
`domi` user, "Domi mode" and the name `domi-pc`.

None of this would exist without her: she was the reason to build it, and every piece (the isolation, the panel,
the cover art, the `off` that gives everything back) is meant so she can play in peace and so can I. Thank you, Domi.

If it helps you share your PC with someone you love, that's the best reason to use it.

## License

[MIT](LICENSE).
