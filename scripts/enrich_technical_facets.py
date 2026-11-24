"""Add cheap technical facets (B&W/color) to already scraped data.

This is a fallback for works without a full VLM review: pixel saturation is
enough to tell an essentially monochrome image from a color one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.technical import merge_color_facets

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"


def process(data_path: Path) -> tuple[int, int]:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    changed = 0
    total = 0
    for photo in data.get("photos") or []:
        total += 1
        image = (photo.get("image") or {}).get("full") or ""
        if not image:
            continue
        image_path = data_path.parent / image
        if not image_path.exists():
            continue
        facets = photo.setdefault("facets", {})
        before = list(facets.get("color") or [])
        merge_color_facets(facets, image_path)
        if facets.get("color") != before:
            changed += 1
    if changed:
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return total, changed


def main() -> int:
    files = sorted(CATALOG.glob("nominations/*/*/data.json")) + sorted(
        CATALOG.glob("themes/*/*/data.json")
    )
    total_photos = 0
    total_changed = 0
    for path in files:
        total, changed = process(path)
        total_photos += total
        total_changed += changed
        print(f"{path.relative_to(ROOT)}: {changed}/{total} updated")
    print(f"Total: {total_changed}/{total_photos} photos updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
