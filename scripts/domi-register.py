#!/usr/bin/env python3
"""Registra un juego ya copiado en /srv/juegos: catálogo + portadas automáticas + Steam si está cerrado.

Uso (como domi; la API key de SteamGridDB opcional por stdin):
    domi-register.py "<nombre>" /srv/juegos/<carpeta>[/<juego>.exe] < key
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sgdb as sg  # noqa: E402
import steamshortcuts as ss  # noqa: E402


def main() -> int:
    name, target = sys.argv[1], Path(sys.argv[2]).resolve()
    exe = ss.guess_exe(target) if target.is_dir() else target
    if exe is None:
        print(f"No encontré un .exe de juego dentro de {target}", file=sys.stderr)
        return 1
    print(f"ejecutable: {exe}")
    if ss.GAMES_ROOT not in exe.parents or not exe.is_file():
        print(f"El .exe debe existir dentro de {ss.GAMES_ROOT}: {exe}", file=sys.stderr)
        return 1
    sg.KEY = "" if sys.stdin.isatty() else sys.stdin.readline().strip()
    appid = ss.shortcut_appid(f'"{exe}"', name)
    ss.catalog_put_game(appid, name, exe, ss.DEFAULT_TOOL, "")
    print(f"catálogo: {name} (appid {appid})")

    if sg.KEY:
        try:
            gid = sg.best_game_id(name)
            got = []
            for kind in sg.KINDS:
                items = sg.list_assets(gid, kind) if gid else []
                if items:
                    body, ext = sg.download(items[0]["url"])
                    ss.save_art(appid, kind, body, ext)
                    got.append(kind)
            print("portadas: " + (", ".join(got) if got else "no encontradas en SteamGridDB"))
        except Exception as e:  # noqa: BLE001
            print(f"portadas: error ({e})")

    if ss.steam_running():
        print("Steam de Domi abierto: se añadirá a Steam cuando cierre la sesión.")
    elif not ss.user_dirs():
        print("Steam de Domi sin cuenta aún: se añadirá tras su primer inicio de sesión.")
    else:
        for line in ss.sync():
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
