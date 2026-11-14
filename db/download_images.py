"""Download catalogue images into web/public/media.

Pages only use these local files. A college with no downloaded file stays blank.
From the repo root, after the catalogue import:

    python db/download_images.py
"""

import mimetypes
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psycopg.types.json import Json

from api.db import connect, database_name

MEDIA = ROOT / "web" / "public" / "media" / "colleges"
MAX_BYTES = 8_000_000
TIMEOUT = 20


def extension(url, content_type):
    guessed = mimetypes.guess_extension((content_type or "").split(";")[0].strip()) or ""
    if guessed in {".jpe", ".jpeg"}:
        guessed = ".jpg"
    if guessed in {".jpg", ".png", ".webp", ".gif"}:
        return guessed
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def download(url, destination):
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    if not url or not url.startswith("https://"):
        return False
    request = Request(url, headers={"User-Agent": "AdmissionSetu/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            payload = response.read(MAX_BYTES + 1)
            kind = response.headers.get("Content-Type", "")
    except (HTTPError, URLError, TimeoutError, OSError):
        return False
    image_url = url.lower().split("?", 1)[0]
    known_image = image_url.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))
    if not payload or len(payload) > MAX_BYTES:
        return None
    if not kind.startswith("image/") and not known_image:
        return None
    destination = destination.with_suffix(extension(url, kind))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(destination)
    return destination


def public_path(path):
    relative = path.relative_to(ROOT / "web" / "public").as_posix()
    return f"/{relative}"


def stored_file(path_value):
    if not path_value or not path_value.startswith("/media/"):
        return None
    local = ROOT / "web" / "public" / path_value.lstrip("/")
    if local.exists() and local.stat().st_size > 0:
        return path_value
    return None


def save_one(url, folder, stem):
    existing = list(folder.glob(f"{stem}.*")) if folder.exists() else []
    for path in existing:
        if path.suffix != ".part" and path.stat().st_size > 0:
            return public_path(path)
    saved = download(url, folder / f"{stem}.img")
    if not saved:
        return None
    return public_path(saved)


def main():
    print(f"Downloading images for database {database_name()}")
    saved = 0
    skipped = 0
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT slug, image_url, logo_url, gallery, image_path, logo_path, gallery_paths
                FROM colleges
                WHERE image_url IS NOT NULL OR logo_url IS NOT NULL OR gallery IS NOT NULL
                ORDER BY slug
                """
            )
            colleges = cursor.fetchall()
        for index, college in enumerate(colleges, 1):
            folder = MEDIA / college["slug"]
            image_path = stored_file(college["image_path"]) or save_one(
                college["image_url"], folder, "hero"
            )
            logo_path = stored_file(college["logo_path"]) or save_one(
                college["logo_url"], folder, "logo"
            )
            gallery_paths = []
            for number, url in enumerate(college["gallery"] or [], 1):
                if not isinstance(url, str):
                    continue
                path = save_one(url, folder, f"gallery-{number}")
                if path:
                    gallery_paths.append(path)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE colleges
                    SET image_path = %s, logo_path = %s, gallery_paths = %s
                    WHERE slug = %s
                    """,
                    (image_path, logo_path, Json(gallery_paths) if gallery_paths else None, college["slug"]),
                )
            connection.commit()
            if image_path or logo_path or gallery_paths:
                saved += 1
            else:
                skipped += 1
            if index % 100 == 0:
                print(f"checked {index} colleges")
    print(f"Colleges with a local image: {saved}. Still blank: {skipped}.")


if __name__ == "__main__":
    main()
