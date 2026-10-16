"""Cliente mínimo de la API v2 de SteamGridDB."""
import json
import urllib.parse
import urllib.request

API = "https://www.steamgriddb.com/api/v2"
KEY = ""  # lo fija quien importa el módulo
CDN_HOSTS = {"cdn2.steamgriddb.com", "cdn.steamgriddb.com"}

# Tipo de asset -> (endpoint, parámetros)
KINDS = {
    "grid": ("grids", {"dimensions": "600x900", "mimes": "image/png,image/jpeg"}),
    "wide": ("grids", {"dimensions": "920x430,460x215", "mimes": "image/png,image/jpeg"}),
    "hero": ("heroes", {"mimes": "image/png,image/jpeg"}),
    "logo": ("logos", {"mimes": "image/png"}),
    "icon": ("icons", {"mimes": "image/png"}),
}


def sgdb(path: str, params: dict | None = None):
    qs = "?" + urllib.parse.urlencode({**(params or {}), "nsfw": "false", "humor": "false"}) if params is not None else ""
    req = urllib.request.Request(f"{API}/{path}{qs}", headers={"Authorization": f"Bearer {KEY}", "User-Agent": "domi-pc"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    if not data.get("success"):
        raise RuntimeError(data.get("errors") or "SteamGridDB error")
    return data["data"]


def list_assets(game_id: int, kind: str) -> list[dict]:
    endpoint, params = KINDS[kind]
    items = sgdb(f"{endpoint}/game/{game_id}", params)
    items.sort(key=lambda a: (a.get("style") != "official", -a.get("score", 0)))
    return [{k: a.get(k) for k in ("id", "url", "thumb", "width", "height", "style", "mime")} for a in items[:40]]


def download(url: str) -> tuple[bytes, str]:
    u = urllib.parse.urlparse(url)
    if u.scheme != "https" or u.hostname not in CDN_HOSTS:
        raise ValueError("URL no permitida")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "domi-pc"}), timeout=60) as r:
        body = r.read(25 * 1024 * 1024)
    ext = ".jpg" if url.lower().endswith((".jpg", ".jpeg")) else ".png"
    return body, ext




def best_game_id(name: str) -> int | None:
    res = sgdb(f"search/autocomplete/{urllib.parse.quote(name, safe='')}")
    return res[0]["id"] if res else None
