"""Cheap technical image checks that do not require a full VLM pass."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat


def detect_color_facets(path: Path) -> list[str]:
    """Return basic color facets from pixel saturation.

    This intentionally only answers a narrow question: is the image essentially
    black and white? It is not a substitute for a VLM review of palette,
    lighting or mood.
    """
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((512, 512))
            saturation = ImageStat.Stat(image.convert("HSV")).mean[1]
    except Exception:
        return []

    if saturation < 6:
        return ["bw"]
    if saturation < 20:
        return ["color", "muted"]
    return ["color"]


def merge_color_facets(facets: dict, path: Path) -> None:
    detected = detect_color_facets(path)
    if not detected:
        return
    current = list(facets.get("color") or [])
    for value in detected:
        if value not in current:
            current.append(value)
    facets["color"] = current
