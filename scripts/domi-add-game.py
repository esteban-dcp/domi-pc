#!/usr/bin/env python3
"""Registra un juego no-Steam en el Steam de domi con Proton forzado.

Uso (como domi, con Steam CERRADO):
    domictl add-game "Paralives" /srv/juegos/Paralives/Paralives.exe
Idempotente: si ya existe un acceso con el mismo nombre, lo reemplaza.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import steamshortcuts as ss  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("exe", type=Path)
    ap.add_argument("--tool", default=ss.DEFAULT_TOOL)
    ap.add_argument("--launch-options", default="")
    args = ap.parse_args()

    if not args.exe.is_file():
        print(f"No existe: {args.exe}", file=sys.stderr)
        return 1
    if ss.steam_running():
        print("Steam de Domi está abierto; ciérralo primero (pisaría los cambios al salir).", file=sys.stderr)
        return 2
    appid = ss.add_shortcut(args.name, args.exe, args.tool, args.launch_options)
    print(f"OK: {args.name} -> appid {appid} ({args.tool})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
