"""CLI: scrape one completed thematic contest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.pipeline import load_config
from scraper.theme_pipeline import scrape_theme


def main() -> int:
    config = load_config()
    parser = argparse.ArgumentParser(description="Scrape a completed 35AWARDS theme")
    parser.add_argument("--theme", required=True, choices=sorted(config.get("themes", {}).keys()))
    parser.add_argument("--limit", type=int, default=0, help="max BEST OF CONTEST works; 0 = all")
    parser.add_argument("--refresh-authors", action="store_true")
    args = parser.parse_args()
    scrape_theme(
        theme_slug=args.theme,
        limit=args.limit,
        refresh_authors=args.refresh_authors,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
