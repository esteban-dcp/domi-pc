"""Accesos directos no-Steam y artwork del Steam de domi (se ejecuta como domi)."""
import binascii
import json
import shutil
import subprocess
import os
import time
from pathlib import Path

import vdf

STEAM = Path.home() / ".local/share/Steam"
DEFAULT_TOOL = "proton-cachyos-native"

# Nombre de archivo en userdata/<id>/config/grid/ por tipo de asset (Big Picture / biblioteca)
ART_SUFFIX = {
    "grid": "p",       # cápsula vertical 600x900
    "wide": "",        # cabecera horizontal 920x430
    "hero": "_hero",   # fondo de la página del juego
    "logo": "_logo",   # logo sobre el hero
    "icon": "_icon",   # icono
}
ART_EXTS = (".png", ".jpg", ".jpeg")

# Catálogo independiente de la cuenta de Steam: sobrevive a cambios de cuenta y se
# reaplica con sync(). El appid de un acceso solo depende de exe+nombre, así que es estable.
CATALOG = Path("/srv/juegos/.catalogo")
CATALOG_JSON = CATALOG / "catalogo.json"
CATALOG_ART = CATALOG / "art"


def shortcut_appid(exe_quoted: str, name: str) -> int:
    """AppID que Steam calcula para accesos no-Steam (unsigned 32-bit)."""
    return (binascii.crc32((exe_quoted + name).encode("utf-8")) & 0xFFFFFFFF) | 0x80000000


def _signed(n: int) -> int:
    return n - 0x100000000 if n >= 0x80000000 else n


def _backup(path: Path) -> None:
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + f".bak-{int(time.time())}"))


def steam_running() -> bool:
    return subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "steam"], capture_output=True).returncode == 0


def user_dirs() -> list[Path]:
    return [p for p in (STEAM / "userdata").glob("*") if p.is_dir() and p.name != "0"]


def _load_shortcuts(userdir: Path) -> dict:
    path = userdir / "config/shortcuts.vdf"
    if path.exists():
        with open(path, "rb") as f:
            return vdf.binary_load(f)
    return {"shortcuts": {}}


def list_shortcuts() -> list[dict]:
    """Accesos no-Steam de todas las cuentas (sin duplicados por appid)."""
    seen, out = set(), []
    for u in user_dirs():
        for s in _load_shortcuts(u).get("shortcuts", {}).values():
            appid = int(s.get("appid", 0)) & 0xFFFFFFFF
            if appid in seen:
                continue
            seen.add(appid)
            out.append({
                "appid": appid,
                "name": s.get("AppName", s.get("appname", "")),
                "exe": s.get("Exe", s.get("exe", "")).strip('"'),
            })
    return sorted(out, key=lambda x: x["name"].lower())


def add_shortcut(name: str, exe: Path, tool: str = DEFAULT_TOOL, launch_options: str = "") -> int:
    """Crea/reemplaza el acceso en todas las cuentas y fuerza Proton. Steam debe estar cerrado."""
    exe = exe.resolve()
    appid = shortcut_appid(f'"{exe}"', name)
    users = user_dirs()
    if not users:
        raise RuntimeError("No hay cuentas en userdata; inicia sesión en Steam primero.")
    for u in users:
        data = _load_shortcuts(u)
        kept = [s for s in data.get("shortcuts", {}).values()
                if s.get("AppName", s.get("appname")) != name]
        prev_icon = ""
        icon_file = find_art(u, appid, "icon")
        if icon_file:
            prev_icon = str(icon_file)
        kept.append({
            "appid": _signed(appid), "AppName": name, "Exe": f'"{exe}"',
            "StartDir": f'"{exe.parent}"', "icon": prev_icon or str(exe), "ShortcutPath": "",
            "LaunchOptions": launch_options, "IsHidden": 0, "AllowDesktopConfig": 1,
            "AllowOverlay": 1, "OpenVR": 0, "Devkit": 0, "DevkitGameID": "",
            "DevkitOverrideAppID": 0, "LastPlayTime": 0, "FlatpakAppID": "", "tags": {},
        })
        data["shortcuts"] = {str(i): s for i, s in enumerate(kept)}
        path = u / "config/shortcuts.vdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        _backup(path)
        with open(path, "wb") as f:
            vdf.binary_dump(data, f)
    if tool:
        set_compat_tool(appid, tool)
    catalog_put_game(appid, name, exe, tool, launch_options)
    return appid


def set_shortcut_icon(appid: int, icon_path: Path) -> None:
    """Apunta el campo icon del acceso al archivo dado. Steam debe estar cerrado."""
    for u in user_dirs():
        data = _load_shortcuts(u)
        changed = False
        for s in data.get("shortcuts", {}).values():
            if int(s.get("appid", 0)) & 0xFFFFFFFF == appid:
                s["icon"] = str(icon_path)
                changed = True
        if changed:
            path = u / "config/shortcuts.vdf"
            _backup(path)
            with open(path, "wb") as f:
                vdf.binary_dump(data, f)


def set_compat_tool(appid: int, tool: str) -> None:
    path = STEAM / "config/config.vdf"
    with open(path, encoding="utf-8") as f:
        data = vdf.load(f, mapper=vdf.VDFDict)
    node = data
    for key in ("InstallConfigStore", "Software", "Valve", "Steam", "CompatToolMapping"):
        match = next((k for k in node.keys() if k.lower() == key.lower()), None)
        if match is None:
            node[key] = vdf.VDFDict()
            match = key
        node = node[match]
    if str(appid) in node:
        del node[str(appid)]
    node[str(appid)] = vdf.VDFDict([("name", tool), ("config", ""), ("priority", "250")])
    _backup(path)
    with open(path, "w", encoding="utf-8") as f:
        vdf.dump(data, f, pretty=True)


def grid_dir(userdir: Path) -> Path:
    return userdir / "config/grid"


def find_art(userdir: Path, appid: int, kind: str) -> Path | None:
    base = grid_dir(userdir) / f"{appid}{ART_SUFFIX[kind]}"
    for ext in ART_EXTS:
        p = base.with_name(base.name + ext)
        if p.exists():
            return p
    return None


def _write_art(directory: Path, appid: int, kind: str, content: bytes, ext: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{appid}{ART_SUFFIX[kind]}"
    for old in ART_EXTS:
        (directory / f"{stem}{old}").unlink(missing_ok=True)
    dest = directory / f"{stem}{ext}"
    dest.write_bytes(content)
    return dest


def save_art(appid: int, kind: str, content: bytes, ext: str) -> list[Path]:
    """Guarda el asset en el catálogo y en todas las cuentas presentes."""
    _write_art(CATALOG_ART, appid, kind, content, ext)
    return [_write_art(grid_dir(u), appid, kind, content, ext) for u in user_dirs()]


def _catalog_load() -> dict:
    if CATALOG_JSON.exists():
        return json.loads(CATALOG_JSON.read_text())
    return {"games": {}}


def catalog_put_game(appid: int, name: str, exe: Path, tool: str, launch_options: str) -> None:
    CATALOG.mkdir(parents=True, exist_ok=True)
    data = _catalog_load()
    data["games"][str(appid)] = {"name": name, "exe": str(exe), "tool": tool, "launch_options": launch_options}
    tmp = CATALOG_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(CATALOG_JSON)


def catalog_import() -> int:
    """Copia al catálogo los accesos y el artwork que ya existan en cualquier cuenta."""
    data = _catalog_load()
    added = 0
    for u in user_dirs():
        for s in _load_shortcuts(u).get("shortcuts", {}).values():
            appid = int(s.get("appid", 0)) & 0xFFFFFFFF
            exe = s.get("Exe", s.get("exe", "")).strip('"')
            if str(appid) not in data["games"] and exe.startswith("/srv/juegos/"):
                catalog_put_game(appid, s.get("AppName", s.get("appname", "")), Path(exe), DEFAULT_TOOL,
                                 s.get("LaunchOptions", ""))
                data = _catalog_load()
                added += 1
            for kind in ART_SUFFIX:
                src = find_art(u, appid, kind)
                if src and not _find_in(CATALOG_ART, appid, kind):
                    _write_art(CATALOG_ART, appid, kind, src.read_bytes(), src.suffix)
    return added


def _find_in(directory: Path, appid: int, kind: str) -> Path | None:
    for ext in ART_EXTS:
        p = directory / f"{appid}{ART_SUFFIX[kind]}{ext}"
        if p.exists():
            return p
    return None


def sync() -> list[str]:
    """Aplica el catálogo a todas las cuentas de Steam de domi. Steam debe estar cerrado."""
    catalog_import()
    done = []
    for appid_s, g in _catalog_load()["games"].items():
        exe = Path(g["exe"])
        if not exe.is_file():
            done.append(f"{g['name']}: falta {exe} (omitido)")
            continue
        appid = add_shortcut(g["name"], exe, g.get("tool", DEFAULT_TOOL), g.get("launch_options", ""))
        for kind in ART_SUFFIX:
            src = _find_in(CATALOG_ART, appid, kind)
            if src:
                for u in user_dirs():
                    _write_art(grid_dir(u), appid, kind, src.read_bytes(), src.suffix)
        icon = _find_in(CATALOG_ART, appid, "icon")
        if icon:
            set_shortcut_icon(appid, icon)
        done.append(f"{g['name']}: ok")
    return done


# ---------------------------------------------------------------- gestión / borrado

GAMES_ROOT = Path("/srv/juegos")
EXE_SKIP = ("unitycrashhandler", "unins", "vc_redist", "vcredist", "dxsetup", "crashreport",
            "setup", "install", "launcher_helper", "dotnet", "directx", "ue4prereq", "uninstall")


def game_folder(exe: Path) -> Path | None:
    """Carpeta de primer nivel en /srv/juegos que contiene el exe."""
    try:
        rel = Path(exe).resolve().relative_to(GAMES_ROOT)
    except ValueError:
        return None
    return GAMES_ROOT / rel.parts[0] if rel.parts else None


def guess_exe(folder: Path) -> Path | None:
    """Elige el .exe principal: mismo nombre que la carpeta, si no el más grande poco profundo."""
    cands = [p for p in folder.rglob("*.exe")
             if len(p.relative_to(folder).parts) <= 3 and not p.name.lower().startswith(EXE_SKIP)]
    if not cands:
        return None
    key = folder.name.lower().replace(" ", "").replace("-", "").replace("_", "")
    for p in cands:
        if p.stem.lower().replace(" ", "").replace("-", "").replace("_", "") == key:
            return p
    return max(cands, key=lambda p: (-len(p.relative_to(folder).parts), p.stat().st_size))


def dir_size(path: Path) -> int:
    out = subprocess.run(["du", "-sb", str(path)], capture_output=True, text=True)
    return int(out.stdout.split()[0]) if out.returncode == 0 and out.stdout else 0


def catalog_games() -> dict:
    return _catalog_load()["games"]


def remove_game(appid: int, delete_files: bool, delete_saves: bool) -> list[str]:
    """Quita el juego de Steam (todas las cuentas), del catálogo y opcionalmente del disco.
    Steam debe estar cerrado."""
    log = []
    data = _catalog_load()
    entry = data["games"].pop(str(appid), None)
    exe = Path(entry["exe"]) if entry else None
    # accesos directos
    for u in user_dirs():
        sc = _load_shortcuts(u)
        items = list(sc.get("shortcuts", {}).values())
        kept = [s for s in items if int(s.get("appid", 0)) & 0xFFFFFFFF != appid]
        if exe is None:
            for s in items:
                if int(s.get("appid", 0)) & 0xFFFFFFFF == appid:
                    exe = Path(s.get("Exe", s.get("exe", "")).strip('"'))
        if len(kept) != len(items):
            sc["shortcuts"] = {str(i): s for i, s in enumerate(kept)}
            path = u / "config/shortcuts.vdf"
            _backup(path)
            with open(path, "wb") as f:
                vdf.binary_dump(sc, f)
            log.append(f"acceso quitado ({u.name})")
        for kind in ART_SUFFIX:
            p = find_art(u, appid, kind)
            if p:
                p.unlink()
    for kind in ART_SUFFIX:
        p = _find_in(CATALOG_ART, appid, kind)
        if p:
            p.unlink()
    tmp = CATALOG_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(CATALOG_JSON)
    log.append("quitado del catálogo")
    # mapeo de Proton
    path = STEAM / "config/config.vdf"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            cfg = vdf.load(f, mapper=vdf.VDFDict)
        node = cfg
        for key in ("InstallConfigStore", "Software", "Valve", "Steam", "CompatToolMapping"):
            match = next((k for k in node.keys() if k.lower() == key.lower()), None)
            if match is None:
                node = None
                break
            node = node[match]
        if node is not None and str(appid) in node:
            del node[str(appid)]
            _backup(path)
            with open(path, "w", encoding="utf-8") as f:
                vdf.dump(cfg, f, pretty=True)
    # archivos
    if delete_files and exe:
        folder = game_folder(exe)
        if folder and folder.is_dir() and folder != GAMES_ROOT:
            shutil.rmtree(folder)
            log.append(f"borrada {folder}")
    if delete_saves:
        prefix = STEAM / "steamapps/compatdata" / str(appid)
        if prefix.is_dir():
            shutil.rmtree(prefix)
            log.append("borradas partidas/prefijo de Proton")
    return log


def rename_game(appid: int, new_name: str) -> int:
    """Cambia el nombre que ve Domi en Steam. El appid depende del nombre, así que se migran las
    portadas, el prefijo de Proton (partidas) y el catálogo al appid nuevo. Steam debe estar cerrado."""
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("El nombre no puede estar vacío")
    data = _catalog_load()
    entry = data["games"].get(str(appid))
    if not entry:
        raise ValueError("Juego desconocido (no está en el catálogo)")
    exe, tool = Path(entry["exe"]), entry.get("tool", DEFAULT_TOOL)
    launch = entry.get("launch_options", "")
    new_appid = shortcut_appid(f'"{exe}"', new_name)
    if new_appid == appid:
        return appid
    if str(new_appid) in data["games"]:
        raise ValueError("Ya hay un juego con ese nombre")
    users = user_dirs()
    arts = {}
    for kind in ART_SUFFIX:
        src = _find_in(CATALOG_ART, appid, kind) or next((p for u in users if (p := find_art(u, appid, kind))), None)
        if src:
            arts[kind] = (src.read_bytes(), src.suffix)
    old_prefix = STEAM / "steamapps/compatdata" / str(appid)
    new_prefix = STEAM / "steamapps/compatdata" / str(new_appid)
    remove_game(appid, False, False)          # acceso, portadas, catálogo y mapeo de Proton (sin tocar archivos ni partidas)
    if old_prefix.is_dir() and not new_prefix.exists():
        old_prefix.rename(new_prefix)         # conserva partidas y configuración de Proton
    add_shortcut(new_name, exe, tool, launch)
    for kind, (body, ext) in arts.items():
        save_art(new_appid, kind, body, ext)
    icon = _find_in(CATALOG_ART, new_appid, "icon")
    if icon:
        set_shortcut_icon(new_appid, icon)
    return new_appid
