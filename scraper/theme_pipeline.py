"""Scrape a completed thematic contest (subcontest) into the catalog."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .authors import AuthorProfile
from .client import BASE_URL, HttpClient
from .media import download_avatar, download_flag, download_photo, make_thumb, safe_slug
from .photodata import fetch_photo_data
from .technical import merge_color_facets
from .pipeline import (
    CATALOG_DIR,
    badge_tier,
    load_analyses,
    load_author,
    load_config,
)
from .themes import parse_theme_results


def scrape_theme(*, theme_slug: str, limit: int = 0, refresh_authors: bool = False) -> Path:
    config = load_config()
    theme = config.get("themes", {}).get(theme_slug)
    if not theme:
        raise SystemExit(f"Unknown theme: {theme_slug}")

    contest_id = int(theme["contest_id"])
    title = theme["title"]
    url = f"{BASE_URL}/page/contests/num/{contest_id}/"

    client = HttpClient()
    analyses = load_analyses()
    parsed = parse_theme_results(
        client.get_text(url), limit=None if limit == 0 else limit
    )
    stubs = [
        stub
        for stub in parsed.photos
        if "BEST OF CONTEST" in (stub.award or "").upper()
    ]
    if stubs:
        selection = "best_of_contest"
        selection_label = "BEST OF CONTEST"
    else:
        stubs = parsed.photos[: limit or 10]
        selection = "top"
        selection_label = "TOP-10"
    if limit > 0:
        stubs = stubs[:limit]
    if not stubs:
        raise RuntimeError(f"No photos found for theme {theme_slug}")

    theme_dir = CATALOG_DIR / "themes" / theme_slug / str(contest_id)
    full_dir = theme_dir / "photos" / "full"
    thumb_dir = theme_dir / "photos" / "thumb"
    avatar_dir = theme_dir / "avatars"
    flags_dir = CATALOG_DIR / "assets" / "flags"
    badges_dir = CATALOG_DIR / "assets" / "badges"
    for directory in (full_dir, thumb_dir, avatar_dir, flags_dir, badges_dir):
        directory.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    profiles: dict[str, AuthorProfile] = {}

    print(f"→ {url}  ({parsed.title or title})")
    for stub in stubs:
        print(f"  {stub.rank:02d}/{len(stubs):02d}  photo {stub.photo_id}  {stub.author_name or stub.author_slug}")
        photo = fetch_photo_data(client, stub.photo_id, referer=url)

        profile = profiles.get(stub.author_slug)
        if profile is None:
            profile = load_author(client, stub, refresh=refresh_authors)
            profiles[stub.author_slug] = profile

        base_name = f"{stub.rank:02d}_{safe_slug(stub.author_slug or stub.author_name)}_{stub.photo_id}"
        full_path = full_dir / f"{base_name}.jpg"
        thumb_path = thumb_dir / f"{base_name}.jpg"
        source_url = photo.image_url or stub.image_url
        ok, width, height = download_photo(
            client, source_url, full_path, fallback_url=stub.image_url
        )
        if ok and not thumb_path.exists():
            make_thumb(full_path, thumb_path)
        if not ok and not thumb_path.exists():
            print("    skip: image unavailable")
            continue

        avatar_name = f"{safe_slug(stub.author_slug)}.jpg"
        avatar_path = avatar_dir / avatar_name
        avatar_url = profile.avatar_url or photo.author_avatar
        if not avatar_path.exists():
            download_avatar(client, avatar_url, avatar_path)

        country_code = stub.country_code
        flag_name = ""
        if country_code:
            flag_name = f"{country_code.lower()}.svg"
            flag_path = flags_dir / flag_name
            if not flag_path.exists():
                download_flag(client, country_code, flag_path)
            if not flag_path.exists():
                flag_name = ""

        award_label = stub.award
        tier = badge_tier(award_label) if award_label else "other"
        award = (
            {
                "label": award_label,
                "kind": tier,
                "tier": tier,
                "contest": title,
                "contest_key": f"theme:{contest_id}",
                "contest_id": str(contest_id),
                "under_id": "",
                "type": "theme",
                "link": url,
            }
            if award_label
            else None
        )
        honours = [award] if award else []

        analysis = analyses.get(str(stub.photo_id))
        facets: dict[str, list[str]] = {}
        if analysis:
            facets = {
                group: list(values)
                for group, values in (analysis.get("facets") or {}).items()
                if isinstance(values, list)
            }
        for group in ("light", "color", "emotion", "image", "season", "technique", "focal"):
            facets.setdefault(group, [])
        if not facets["season"]:
            facets["season"] = ["unspecified"]
        if ok:
            merge_color_facets(facets, full_path)
        facets["award"] = (
            [tier] if award and tier in {"win", "best", "top", "stage"} else []
        )
        facets["source"] = ["theme"]
        facets["theme"] = [theme_slug]
        if theme.get("year"):
            facets["year"] = [str(theme["year"])]

        memberships = [
            {
                "name": contest.name,
                "under_title": contest.under_title,
                "type": contest.entity_type,
                "contest_id": contest.contest_id,
                "under_id": contest.under_id,
                "link": contest.link,
                "badge": contest.badge_label,
                "tier": badge_tier(contest.badge_label),
            }
            for contest in photo.contests
            if contest.entity_type in {"nomination", "theme"}
        ]

        records.append(
            {
                "rank": stub.rank,
                "id": stub.photo_id,
                "title": photo.title,
                "description": photo.description,
                "page_url": f"{url}#photo_{stub.photo_id}",
                "source_url": f"{BASE_URL}/gallery/photo/{stub.photo_id}/",
                "top35": False,
                "image": {
                    "source": source_url,
                    "full": f"photos/full/{base_name}.jpg" if ok else "",
                    "thumb": f"photos/thumb/{base_name}.jpg" if thumb_path.exists() else "",
                    "width": width,
                    "height": height,
                },
                "award": award,
                "honours": honours,
                "badge_images": [],
                "analysis": analysis,
                "facets": facets,
                "memberships": memberships,
                "metrics": {
                    "views": photo.views,
                    "likes": photo.likes,
                    "favorites": photo.favorites,
                },
                "author": {
                    "slug": stub.author_slug,
                    "name": photo.author_name or profile.name_native or stub.author_name,
                    "name_ru": profile.name,
                    "name_native": profile.name_native,
                    "profile_url": stub.author_url or f"{BASE_URL}/author/{stub.author_slug}/",
                    "external_profile": stub.external_profile
                    or next((u for u in profile.same_as if "35photo.pro" in u), ""),
                    "avatar": f"avatars/{avatar_name}" if avatar_path.exists() else "",
                    "country": profile.country or stub.country,
                    "country_code": country_code,
                    "flag": f"assets/flags/{flag_name}" if flag_name else "",
                    "city": profile.city or stub.city,
                    "followers": profile.followers or photo.followers,
                    "following": profile.following,
                    "photos_count": profile.photos_count,
                    "rank_in_nomination": None,
                    "genres": profile.genres,
                    "gear": profile.gear,
                },
            }
        )

    data = {
        "schema_version": 1,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "theme": {
            "slug": theme_slug,
            "title": title,
            "name_ru": theme.get("name_ru", ""),
            "contest_id": contest_id,
            "year": theme.get("year"),
            "category": theme.get("category", ""),
            "description_ru": theme.get("description_ru", ""),
            "source_url": url,
            "selection": selection,
            "selection_label": selection_label,
        },
        "limit": len(records),
        "selection": "best_of_contest",
        "photos": records,
    }
    data_path = theme_dir / "data.json"
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(records)} theme photos -> {data_path}")
    return data_path
