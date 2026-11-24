"""Media downloads and local thumbnail generation."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

from .client import HttpClient

PHOTO_REFERER = "https://35awards.com/winners11th/nomination/1197/"


def safe_slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "author"


def download_photo(
    client: HttpClient, url: str, dest: Path, *, fallback_url: str = ""
) -> tuple[bool, int, int]:
    """Download a photo and return (ok, width, height)."""
    sources = [url, fallback_url] if fallback_url else [url]
    for source in sources:
        if not source:
            continue
        temp = dest.with_suffix(dest.suffix + ".part")
        if not client.download(source, temp, referer=PHOTO_REFERER):
            temp.unlink(missing_ok=True)
            continue
        try:
            with Image.open(temp) as image:
                width, height = image.size
        except Exception:
            temp.unlink(missing_ok=True)
            continue
        temp.replace(dest)
        return True, width, height
    return False, 0, 0


def make_thumb(source: Path, dest: Path, *, max_width: int = 720, quality: int = 82) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        if image.width > max_width:
            ratio = max_width / image.width
            image = image.resize(
                (max_width, max(1, round(image.height * ratio))),
                Image.Resampling.LANCZOS,
            )
        image.save(dest, "JPEG", quality=quality, optimize=True, progressive=True)


def download_avatar(
    client: HttpClient, url: str, dest: Path, *, max_size: int = 240
) -> bool:
    if not url:
        return False
    temp = dest.with_suffix(dest.suffix + ".part")
    if not client.download(url, temp, referer="https://35awards.com/"):
        temp.unlink(missing_ok=True)
        return False
    try:
        with Image.open(temp) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            dest.parent.mkdir(parents=True, exist_ok=True)
            image.save(dest, "JPEG", quality=86, optimize=True)
    except Exception:
        temp.unlink(missing_ok=True)
        return False
    temp.unlink(missing_ok=True)
    # 35awards returns a tiny grey "no photo" placeholder for authors without
    # an avatar. Treat it as missing instead of showing it in the catalog.
    if dest.stat().st_size < 2200:
        is_placeholder = False
        try:
            with Image.open(dest) as image:
                is_placeholder = image.size in ((48, 48), (150, 150))
        except Exception:
            pass
        if is_placeholder:
            dest.unlink(missing_ok=True)
            return False
    return True


def download_flag(client: HttpClient, country_code: str, dest: Path) -> bool:
    if not country_code or len(country_code) != 2:
        return False
    url = f"https://flagcdn.com/{country_code.lower()}.svg"
    if client.download(url, dest, referer="https://35awards.com/"):
        return True
    # Some networks block flagcdn; a tiny transparent placeholder keeps the
    # markup valid without a broken image icon.
    return False
