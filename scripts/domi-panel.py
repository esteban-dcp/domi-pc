#!/usr/bin/env python3
"""Panel local para los juegos no-Steam de Domi: artwork de SteamGridDB y alta de juegos.

Se ejecuta como domi (escribe en su Steam). Solo escucha en 127.0.0.1 y exige un token
aleatorio en cada petición. Lo lanza `domictl panel`, que le pasa la API key por stdin.
"""
import getpass
import json
import os
import secrets
import shutil
import subprocess
import threading
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import steamshortcuts as ss  # noqa: E402

import sgdb as sg  # noqa: E402

# La API key llega por stdin (domictl la pasa así para no dejarla en argv ni en disco de domi)
sg.KEY = sys.stdin.readline().strip() if os.environ.get("PANEL_KEY_STDIN") else os.environ.get("SGDB_KEY", "").strip()
KEY = sg.KEY
TOKEN = os.environ.get("PANEL_TOKEN") or secrets.token_urlsafe(16)
GAMES_DIR = Path("/srv/juegos")
STATIC_DIR = Path(__file__).resolve().parent / "panel"
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
WRITE_LOCK = threading.Lock()  # shortcuts.vdf/config.vdf no admiten escrituras concurrentes
KINDS, sgdb, list_assets, download = sg.KINDS, sg.sgdb, sg.list_assets, sg.download


def apply_art(appid: int, kind: str, url: str) -> dict:
    body, ext = download(url)
    saved = ss.save_art(appid, kind, body, ext)
    note = ""
    if kind == "icon":
        if ss.steam_running():
            note = "Icono guardado; se asigna al acceso cuando Steam esté cerrado (vuelve a aplicarlo)."
        else:
            ss.set_shortcut_icon(appid, ss._find_in(ss.CATALOG_ART, appid, "icon") or saved[0])
    return {"saved": [str(p) for p in saved], "note": note}


def exe_candidates() -> list[str]:
    if not GAMES_DIR.is_dir():
        return []
    skip = ("unitycrashhandler", "unins", "vc_redist", "dxsetup", "crashreport", "setup")
    out = []
    for p in sorted(GAMES_DIR.glob("*/**/*.exe")):
        if len(p.relative_to(GAMES_DIR).parts) <= 3 and not p.name.lower().startswith(skip):
            out.append(str(p))
    return out


_SIZE_CACHE: dict[str, tuple[float, int]] = {}


def folder_size(folder: Path) -> int:
    """Tamaño de la carpeta del juego (cacheado por mtime, du sobre GB tarda)."""
    try:
        mtime = folder.stat().st_mtime
    except OSError:
        return 0
    hit = _SIZE_CACHE.get(str(folder))
    if hit and hit[0] == mtime:
        return hit[1]
    size = ss.dir_size(folder)
    _SIZE_CACHE[str(folder)] = (mtime, size)
    return size


def games_payload() -> dict:
    """Juegos en Steam + juegos del catálogo aún pendientes de añadir a Steam."""
    games, seen = [], set()
    in_steam = {g["appid"]: g for g in ss.list_shortcuts()}
    catalog = ss.catalog_games()
    for appid_s, c in catalog.items():
        seen.add(int(appid_s))
    for appid in sorted(set(in_steam) | seen):
        g = in_steam.get(appid) or {"appid": appid, "name": catalog[str(appid)]["name"], "exe": catalog[str(appid)]["exe"]}
        art = {k: bool(ss._find_in(ss.CATALOG_ART, appid, k)) for k in ss.ART_SUFFIX}
        folder = ss.game_folder(Path(g["exe"]))
        prefix = ss.STEAM / "steamapps/compatdata" / str(appid)
        games.append({**g, "art": art, "in_steam": appid in in_steam,
                      "size": folder_size(folder) if folder else 0,
                      "saves": folder_size(prefix) if prefix.is_dir() else 0})
    games.sort(key=lambda g: g["name"].lower())
    du = shutil.disk_usage(GAMES_DIR)
    return {"games": games, "steam_running": ss.steam_running(), "exes": exe_candidates(),
            "has_key": bool(KEY), "disk_free": du.free, "disk_total": du.total}


def system_status() -> dict:
    """Estado ligero del modo Domi, legible por el usuario domi sin privilegios."""
    def run(*cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=4).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""
    mem = {k: int(v.split()[0]) for k, v in (l.split(":", 1) for l in open("/proc/meminfo"))}
    mode_on = run("systemctl", "is-active", f"moonshine@{getpass.getuser()}") == "active"
    # nvidia-smi despierta la dGPU: con el modo apagado no se consulta
    gpu = run("nvidia-smi", "--query-gpu=utilization.gpu,utilization.encoder,memory.used,memory.total,power.draw,temperature.gpu",
              "--format=csv,noheader,nounits").split(", ") if mode_on else []
    return {
        "mode_on": mode_on,
        "steam_running": ss.steam_running(),
        "vpn_on": run("systemctl", "is-active", "domi-tailscale") == "active",
        "ram_free_mb": mem["MemAvailable"] // 1024,
        "ram_total_mb": mem["MemTotal"] // 1024,
        "gpu": dict(zip(("util", "enc", "vram", "vram_total", "watts", "temp"), gpu)) if len(gpu) == 6 else None,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "domi-panel"

    def log_message(self, fmt, *args):  # silencioso
        pass

    def _authed(self, qs) -> bool:
        return secrets.compare_digest(self.headers.get("X-Token", "") or qs.get("t", [""])[0], TOKEN)

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode())

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(u.query)
        if not self._authed(qs):
            return self._send(403, b"forbidden", "text/plain")
        try:
            if u.path == "/":
                html = (STATIC_DIR / "index.html").read_text().replace("__TOKEN__", TOKEN)
                return self._send(200, html.encode(), STATIC_TYPES[".html"])
            if u.path.startswith("/static/"):
                f = STATIC_DIR / Path(u.path).name  # solo ficheros planos del directorio panel/
                if f.suffix not in STATIC_TYPES or f.name == "index.html" or not f.is_file():
                    return self._send(404, b"", "text/plain")
                return self._send(200, f.read_bytes(), STATIC_TYPES[f.suffix])
            if u.path == "/api/status":
                return self._json(system_status())
            if u.path == "/api/games":
                return self._json(games_payload())
            if u.path == "/api/search":
                q = qs.get("q", [""])[0].strip()
                res = sgdb(f"search/autocomplete/{urllib.parse.quote(q, safe='')}") if q else []
                return self._json([{"id": int(g["id"]), "name": g["name"], "year": (g.get("release_date") or 0)} for g in res[:15]])
            if u.path == "/api/assets":
                return self._json(list_assets(int(qs["game"][0]), qs["kind"][0]))
            if u.path.startswith("/art/"):
                _, _, appid, kind = u.path.split("/")
                if kind not in ss.ART_SUFFIX:
                    return self._send(404, b"", "text/plain")
                users = ss.user_dirs()
                p = ss._find_in(ss.CATALOG_ART, int(appid), kind) or (users and ss.find_art(users[0], int(appid), kind))
                if not p:
                    return self._send(404, b"", "text/plain")
                return self._send(200, p.read_bytes(), "image/jpeg" if p.suffix != ".png" else "image/png")
            return self._send(404, b"not found", "text/plain")
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 500)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if not self._authed(urllib.parse.parse_qs(u.query)):
            return self._send(403, b"forbidden", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            if u.path == "/api/apply":
                if body.get("kind") not in KINDS:
                    return self._json({"error": "tipo inválido"}, 400)
                with WRITE_LOCK:
                    return self._json(apply_art(int(body["appid"]), body["kind"], body["url"]))
            if u.path == "/api/auto":
                appid, game = int(body["appid"]), int(body["game"])
                done = {}
                with WRITE_LOCK:
                    for kind in KINDS:
                        items = list_assets(game, kind)
                        if items:
                            apply_art(appid, kind, items[0]["url"])
                            done[kind] = True
                return self._json({"applied": done})
            if u.path == "/api/steam-originals":
                appid, game = int(body["appid"]), int(body["game"])
                done, missing = {}, []
                with WRITE_LOCK:
                    for kind in KINDS:
                        orig = sg.steam_original(game, kind)
                        if orig:
                            apply_art(appid, kind, orig["url"])
                            done[kind] = True
                        else:
                            missing.append(kind)
                return self._json({"applied": done, "missing": missing})
            if u.path == "/api/remove":
                if ss.steam_running():
                    return self._json({"error": "Cierra el Steam de Domi (Quit app en Moonlight) para quitar juegos."}, 409)
                with WRITE_LOCK:
                    log = ss.remove_game(int(body["appid"]), bool(body.get("files")), bool(body.get("saves")))
                _SIZE_CACHE.clear()
                return self._json({"log": log})
            if u.path == "/api/rename":
                if ss.steam_running():
                    return self._json({"error": "Cierra el Steam de Domi (Quit app en Moonlight) para renombrar juegos."}, 409)
                with WRITE_LOCK:
                    new_appid = ss.rename_game(int(body["appid"]), str(body["name"]))
                _SIZE_CACHE.clear()
                return self._json({"appid": new_appid})
            if u.path == "/api/add":
                if ss.steam_running():
                    return self._json({"error": "Cierra el Steam de Domi (Quit app en Moonlight) para añadir juegos."}, 409)
                exe = Path(body["exe"]).resolve()
                if GAMES_DIR not in exe.parents or not exe.is_file():
                    return self._json({"error": f"El .exe debe estar dentro de {GAMES_DIR}"}, 400)
                with WRITE_LOCK:
                    appid = ss.add_shortcut(body["name"].strip(), exe)
                return self._json({"appid": appid})
            return self._send(404, b"not found", "text/plain")
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 500)


def main() -> int:
    port = int(os.environ.get("PANEL_PORT", "0"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={TOKEN}"
    print(url, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
