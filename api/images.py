import re
import threading
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException
from fastapi.responses import FileResponse

from api.db import ROOT

MEDIA = ROOT / "web" / "public" / "media"
MAX_BYTES = 8_000_000
_PATH = re.compile(r"^colleges/([a-z0-9-]+)/(hero|logo|gallery-(\d+))$")
_LOCKS = {}
_GUARD = threading.Lock()


def _lock(key):
    with _GUARD:
        if key not in _LOCKS:
            _LOCKS[key] = threading.Lock()
        return _LOCKS[key]


def _extension(url, content_type):
    kind = (content_type or "").split(";")[0].strip().lower()
    if kind == "image/png":
        return ".png"
    if kind == "image/webp":
        return ".webp"
    if kind == "image/gif":
        return ".gif"
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix == ".png":
        return ".png"
    if suffix == ".webp":
        return ".webp"
    if suffix == ".gif":
        return ".gif"
    return ".jpg"


def _existing(folder, name):
    if not folder.exists():
        return None
    for path in folder.glob(f"{name}.*"):
        if path.suffix != ".part" and path.stat().st_size > 0:
            return path
    return None


def _download(url, destination):
    if not url.startswith("https://"):
        return None
    request = Request(url, headers={"User-Agent": "AdmissionSetu/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read(MAX_BYTES + 1)
            kind = response.headers.get("Content-Type", "")
    except (HTTPError, URLError, TimeoutError, OSError):
        return None
    known = url.lower().split("?", 1)[0].endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))
    if not payload or len(payload) > MAX_BYTES:
        return None
    if not kind.startswith("image/") and not known:
        return None
    destination = destination.with_suffix(_extension(url, kind))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(destination)
    return destination


def _source_url(connection, slug, kind, gallery_index):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT image_url, logo_url, gallery
            FROM colleges
            WHERE slug = %s AND is_active IS TRUE
            """,
            (slug,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    if kind == "hero":
        return row["image_url"]
    if kind == "logo":
        return row["logo_url"]
    gallery = row["gallery"] or []
    if gallery_index < 1 or gallery_index > len(gallery):
        return None
    return gallery[gallery_index - 1]


def serve_media(connection, file_path):
    match = _PATH.fullmatch(file_path)
    if not match:
        raise HTTPException(status_code=404, detail="Image not found")
    slug, kind = match.group(1), match.group(2)
    gallery_index = int(match.group(3) or 0)
    name = f"gallery-{gallery_index}" if kind.startswith("gallery-") else kind
    folder = MEDIA / "colleges" / slug
    with _lock(f"{slug}/{name}"):
        saved = _existing(folder, name)
        if saved is None:
            source = _source_url(connection, slug, "gallery" if gallery_index else kind, gallery_index)
            if not isinstance(source, str):
                raise HTTPException(status_code=404, detail="Image not found")
            saved = _download(source, folder / f"{name}.img")
        if saved is None:
            raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(saved)
