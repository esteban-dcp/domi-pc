"""Cliente mínimo de la API v2 de SteamGridDB."""
import json
import urllib.parse
import urllib.request

API = "https://www.steamgriddb.com/api/v2"
KEY = ""  # lo fija quien importa el módulo
CDN_HOSTS = {"cdn2.steamgriddb.com", "cdn.steamgriddb.com",
             "cdn.cloudflare.steamstatic.com", "shared.fastly.steamstatic.com", "cdn.akamai.steamstatic.com"}
STEAM_CDN = "https://cdn.cloudflare.steamstatic.com"
# Tipo de asset -> archivo original en el CDN de Steam (el icono se resuelve aparte, por hash)
STEAM_FILES = {"grid": "library_600x900.jpg", "wide": "header.jpg", "hero": "library_hero.jpg", "logo": "logo.png"}

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


_STEAM_CACHE: dict = {}


def _exists(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "domi-pc"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _pick(lang_map) -> str | None:
    if not isinstance(lang_map, dict) or not lang_map:
        return None
    return lang_map.get("english") or next(iter(lang_map.values()))


def _hashed_url(sid: str, meta: dict, kind: str) -> str | None:
    """Ruta con hash de la versión vigente del asset, según los metadatos de SteamGridDB."""
    field = {"wide": ("header_image_full",), "grid": ("library_capsule_full", "image"),
             "hero": ("library_hero_full", "image"), "logo": ("library_logo_full", "image")}[kind]
    node = meta
    for key in field:
        node = node.get(key) if isinstance(node, dict) else None
    rel = _pick(node)
    return f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{sid}/{rel}" if rel else None


def steam_original(game_id: int, kind: str) -> dict | None:
    """Imagen original de la tienda de Steam para este juego de SteamGridDB (si está en Steam)."""
    if game_id not in _STEAM_CACHE:
        try:
            d = sgdb(f"games/id/{game_id}", {"platformdata": "steam"})
            steam = (d.get("external_platform_data") or {}).get("steam") or []
            _STEAM_CACHE[game_id] = (steam[0]["id"], steam[0].get("metadata") or {}) if steam else None
        except Exception:  # noqa: BLE001
            return None  # fallo puntual: no se cachea
    info = _STEAM_CACHE[game_id]
    if not info:
        return None
    sid, meta = info
    if kind == "icon":
        h = meta.get("icon")
        url = f"https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/{sid}/{h}.jpg" if h else None
    else:
        # La ruta simple (/steam/apps/<id>/header.jpg) puede servir versiones antiguas: la actual va por hash.
        url = _hashed_url(sid, meta, kind)
        if not url or not _exists(url):
            url = f"{STEAM_CDN}/steam/apps/{sid}/{STEAM_FILES[kind]}"
    if not url or not _exists(url):
        return None
    return {"id": f"steam-{kind}", "url": url, "thumb": url, "width": 600 if kind == "grid" else None,
            "height": 900 if kind == "grid" else None, "style": "original de Steam", "mime": None, "steam": True}


def list_assets(game_id: int, kind: str) -> list[dict]:
    endpoint, params = KINDS[kind]
    items = sgdb(f"{endpoint}/game/{game_id}", params)
    items.sort(key=lambda a: (a.get("style") != "official", -a.get("score", 0)))
    out = [{k: a.get(k) for k in ("id", "url", "thumb", "width", "height", "style", "mime")} for a in items[:40]]
    orig = steam_original(game_id, kind)
    if orig:  # el original de Steam va primero (menos el icono: es diminuto, mejor uno de la comunidad por defecto)
        out = out + [orig] if kind == "icon" else [orig] + out
    return out


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
