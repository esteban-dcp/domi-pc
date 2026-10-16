#!/usr/bin/env python3
"""Aplica el catálogo de /srv/juegos/.catalogo a todas las cuentas de Steam de domi (Steam cerrado)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import steamshortcuts as ss  # noqa: E402

if ss.steam_running():
    print("Steam de Domi está abierto; ciérralo primero.", file=sys.stderr)
    sys.exit(2)
if not ss.user_dirs():
    print("Aún no hay cuenta en el Steam de Domi: que inicie sesión una vez y repite.", file=sys.stderr)
    sys.exit(1)
for line in ss.sync():
    print(line)
