"""Collect names/years for every contest context found in photo memberships.

Saves `config/contest_meta.json`; the builder uses it for the context filter
and for membership chips.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup

from scraper.client import HttpClient
from scraper.pipeline import load_config

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
OUT = ROOT / "config" / "contest_meta.json"


def parse_date(value: str) -> str:
    day, month, year = value.split(".")
    return f"20{year}-{month}-{day}"


def main() -> int:
    config = load_config()
    client = HttpClient()
    theme_ids: set[str] = set()
    nomination_ids: set[str] = set()
    nomination_membership_info: dict[str, dict] = {}
    for path in sorted(CATALOG.glob("nominations/*/*/data.json")) + sorted(
        CATALOG.glob("themes/*/*/data.json")
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        for photo in data.get("photos") or []:
            for membership in photo.get("memberships") or []:
                if membership.get("type") == "theme" and membership.get("contest_id"):
                    theme_ids.add(str(membership["contest_id"]))
                elif membership.get("type") == "nomination" and membership.get("under_id"):
                    nomination_id = str(membership["under_id"])
                    nomination_ids.add(nomination_id)
                    key = f"nomination:{nomination_id}"
                    info = nomination_membership_info.setdefault(key, {})
                    if not info.get("title") and membership.get("under_title"):
                        info["title"] = membership["under_title"]
                    if not info.get("edition") and membership.get("name"):
                        info["edition"] = membership["name"]
                    if not info.get("url") and membership.get("link"):
                        info["url"] = membership["link"]

    meta: dict[str, dict] = {}

    # Main nominations: id -> (slug, title, year)
    for slug, nomination in config["nominations"].items():
        for edition_slug, nomination_id in nomination.get("editions", {}).items():
            edition = config["editions"][edition_slug]
            key = f"nomination:{nomination_id}"
            meta[key] = {
                "key": key,
                "type": "nomination",
                "contest_id": str(nomination_id),
                "slug": slug,
                "title": nomination["name"],
                "name_ru": nomination.get("name_ru", ""),
                "year": edition["year"],
            }

    # Nominations that appear only in photo memberships (other categories/years).
    # Their names come from the membership itself, so the context filter never
    # shows a bare "nomination:277".
    for nomination_id in sorted(nomination_ids, key=int):
        key = f"nomination:{nomination_id}"
        if key in meta:
            continue
        info = nomination_membership_info.get(key, {})
        edition = info.get("edition") or ""
        year_match = re.search(r"(20\d{2})", edition)
        meta[key] = {
            "key": key,
            "type": "nomination",
            "contest_id": nomination_id,
            "slug": "",
            "title": info.get("title") or edition or f"Nomination {nomination_id}",
            "name_ru": "",
            "year": int(year_match.group(1)) if year_match else None,
            "url": info.get("url", ""),
        }

    configured_themes = {
        str(theme["contest_id"]): theme for theme in config.get("themes", {}).values()
    }
    existing_meta = (
        json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    )

    for contest_id in sorted(theme_ids, key=int):
        key = f"theme:{contest_id}"
        if existing_meta.get(key, {}).get("title"):
            meta[key] = existing_meta[key]
            continue
        configured = configured_themes.get(contest_id, {})
        title = configured.get("title") or ""
        name_ru = configured.get("name_ru") or ""
        year = configured.get("year")
        start = ""
        end = ""
        url = f"https://35awards.com/page/contests/num/{contest_id}/"
        try:
            soup = BeautifulSoup(client.get_text(url), "lxml")
            h1 = soup.select_one("h1")
            if h1 and not title:
                title = h1.get_text(" ", strip=True)
            text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
            match = re.search(r"Submissions\s*·\s*([0-9.]+)[–-]([0-9.]+)", text)
            if match:
                start = parse_date(match.group(1))
                end = parse_date(match.group(2))
                year = int(end[:4])
        except Exception:
            pass
        meta[key] = {
            "key": key,
            "type": "theme",
            "contest_id": contest_id,
            "title": title or f"Theme {contest_id}",
            "name_ru": name_ru,
            "year": year,
            "start": start,
            "end": end,
            "url": url,
        }

    OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(meta)} contest contexts -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
