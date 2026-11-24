"""CLI: scrape every configured nomination edition.

Default limit is 35 works per nomination/year.

    python scripts/scrape_all.py
    python scripts/scrape_all.py --limit 35
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.pipeline import load_config, scrape


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape all configured 35AWARDS editions")
    parser.add_argument("--limit", type=int, default=35, help="photos per edition (default: 35)")
    parser.add_argument(
        "--refresh-authors", action="store_true", help="ignore the author profile cache"
    )
    args = parser.parse_args()

    config = load_config()
    for nomination_slug, nomination in config["nominations"].items():
        for edition_slug in nomination["editions"]:
            print(f"\n=== {nomination_slug} / {edition_slug} ===")
            scrape(
                nomination_slug=nomination_slug,
                edition_slug=edition_slug,
                limit=args.limit,
                refresh_authors=args.refresh_authors,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
