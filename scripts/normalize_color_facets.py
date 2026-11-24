"""Remove the duplicate `monochrome` facet.

For this catalog `bw` is the single monochrome tag. `monochrome` duplicated it
in every technical facet and made two filters show the same count.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"


def clean_color(facets: dict) -> bool:
    values = facets.get("color")
    if not isinstance(values, list) or "monochrome" not in values:
        return False
    facets["color"] = [value for value in values if value != "monochrome"]
    return True


def main() -> int:
    changed = 0
    analyses_path = ROOT / "analysis" / "analyses.json"
    analyses = json.loads(analyses_path.read_text(encoding="utf-8"))
    for item in analyses.values():
        if clean_color(item.setdefault("facets", {})):
            changed += 1
    analyses_path.write_text(json.dumps(analyses, ensure_ascii=False, indent=2), encoding="utf-8")

    for path in sorted(CATALOG.glob("nominations/*/*/data.json")) + sorted(
        CATALOG.glob("themes/*/*/data.json")
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        local = 0
        for photo in data.get("photos") or []:
            if clean_color(photo.setdefault("facets", {})):
                local += 1
        if local:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            changed += local
    print(f"Removed `monochrome` from {changed} facet sets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
