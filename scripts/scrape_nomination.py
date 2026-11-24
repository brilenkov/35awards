"""CLI: scrape one nomination edition.

Examples:
    python scripts/scrape_nomination.py --nomination female-portrait --edition 11th --limit 10
    python scripts/scrape_nomination.py --nomination female-portrait --edition 11th --limit 35
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.pipeline import ROOT, load_config, scrape


def main() -> int:
    config = load_config()
    parser = argparse.ArgumentParser(description="Scrape a 35AWARDS nomination edition")
    parser.add_argument(
        "--nomination",
        default="female-portrait",
        choices=sorted(config["nominations"].keys()),
        help="nomination slug from config/catalog.json",
    )
    parser.add_argument(
        "--edition",
        default="11th",
        choices=sorted(config["editions"].keys()),
        help="edition slug from config/catalog.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=35,
        help="how many top photos to keep (default: 35)",
    )
    parser.add_argument(
        "--refresh-authors",
        action="store_true",
        help="ignore the local author profile cache",
    )
    args = parser.parse_args()

    scrape(
        nomination_slug=args.nomination,
        edition_slug=args.edition,
        limit=args.limit,
        refresh_authors=args.refresh_authors,
    )
    print(f"Project root: {ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
