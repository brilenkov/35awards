"""Scrape a personal comparison set: top works from thematic contests + author works.

Example:
    python scripts/scrape_author_review.py --profile brilenkov --themes 1083,1074 --top 10
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.authors import fetch_author
from scraper.client import BASE_URL, HttpClient
from scraper.media import download_avatar, download_photo, make_thumb, safe_slug
from scraper.photodata import fetch_photo_data
from scraper.themes import parse_theme_results

ROOT = Path(__file__).resolve().parent.parent


def profile_photo_ids(html: str) -> list[int]:
    return sorted({int(value) for value in re.findall(r"/gallery/photo/(\d+)/", html)})


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a personal contest comparison")
    parser.add_argument("--profile", default="brilenkov", help="35AWARDS author slug")
    parser.add_argument("--themes", default="1083,1074", help="comma-separated contest ids")
    parser.add_argument("--top", type=int, default=10, help="how many winners per theme")
    args = parser.parse_args()

    client = HttpClient()
    profile_url = f"{BASE_URL}/author/{args.profile}/"
    html = client.get_text(profile_url)
    profile = fetch_author(client, profile_url)

    out = ROOT / "catalog" / "reports" / safe_slug(args.profile)
    out.mkdir(parents=True, exist_ok=True)

    avatar_path = out / "mine" / "avatar.jpg"
    if profile.avatar_url:
        download_avatar(client, profile.avatar_url, avatar_path, max_size=240)

    result = {
        "author": {
            "name": profile.name,
            "name_native": profile.name_native,
            "profile_url": profile_url,
            "external_profile": "https://35photo.pro/%s/" % safe_slug(args.profile),
            "city": profile.city,
            "country": profile.country,
            "followers": profile.followers,
            "following": profile.following,
            "photos_count": profile.photos_count,
            "avatar": "mine/avatar.jpg" if avatar_path.exists() else "",
        },
        "themes": [],
        "mine": [],
    }

    for raw_id in args.themes.split(","):
        theme_id = int(raw_id.strip())
        url = f"{BASE_URL}/page/contests/num/{theme_id}/"
        parsed = parse_theme_results(client.get_text(url), limit=args.top)
        theme_dir = out / f"theme-{theme_id}"
        records = []
        print(f"THEME {theme_id}: {parsed.title} ({len(parsed.photos)})")
        for stub in parsed.photos:
            data = fetch_photo_data(client, stub.photo_id, referer=url)
            base = f"{stub.rank:02d}_{safe_slug(stub.author_slug or stub.author_name)}_{stub.photo_id}"
            full = theme_dir / "full" / f"{base}.jpg"
            thumb = theme_dir / "thumb" / f"{base}.jpg"
            ok, width, height = download_photo(
                client,
                data.image_url or stub.image_url,
                full,
                fallback_url=stub.image_url,
            )
            if ok:
                make_thumb(full, thumb)
            records.append(
                {
                    "rank": stub.rank,
                    "id": stub.photo_id,
                    "title": data.title,
                    "award": stub.award,
                    "author": stub.author_name,
                    "author_url": stub.author_url,
                    "image": {
                        "full": f"theme-{theme_id}/full/{base}.jpg" if ok else "",
                        "thumb": f"theme-{theme_id}/thumb/{base}.jpg"
                        if thumb.exists()
                        else "",
                        "width": width,
                        "height": height,
                    },
                    "metrics": {
                        "views": data.views,
                        "likes": data.likes,
                        "favorites": data.favorites,
                    },
                    "page_url": f"{url}#photo_{stub.photo_id}",
                }
            )
        result["themes"].append(
            {"id": theme_id, "title": parsed.title, "url": url, "photos": records}
        )

    theme_ids = {int(item) for item in args.themes.split(",")}
    for photo_id in profile_photo_ids(html):
        data = fetch_photo_data(client, photo_id, referer=profile_url)
        contest = None
        for entry in data.contests:
            if int(entry.contest_id or 0) in theme_ids:
                contest = entry
                break
        if contest is None:
            continue
        base = f"{safe_slug(data.author_name)}_{photo_id}"
        full = out / "mine" / "full" / f"{base}.jpg"
        thumb = out / "mine" / "thumb" / f"{base}.jpg"
        ok, width, height = download_photo(client, data.image_url, full)
        if ok:
            make_thumb(full, thumb)
        result["mine"].append(
            {
                "id": photo_id,
                "title": data.title,
                "contest": contest.name,
                "contest_id": contest.contest_id,
                "contest_url": contest.link,
                "award": contest.badge_label,
                "image": {
                    "full": f"mine/full/{base}.jpg" if ok else "",
                    "thumb": f"mine/thumb/{base}.jpg" if thumb.exists() else "",
                    "width": width,
                    "height": height,
                },
                "metrics": {
                    "views": data.views,
                    "likes": data.likes,
                    "favorites": data.favorites,
                },
                "page_url": f"{BASE_URL}/gallery/photo/{photo_id}/",
            }
        )

    (out / "review.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved {len(result['mine'])} personal works and {len(result['themes'])} themes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
