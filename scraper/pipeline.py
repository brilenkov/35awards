"""End-to-end scrape of one nomination edition into the static catalog tree."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .authors import AuthorProfile, fetch_author
from .client import BASE_URL, HttpClient
from .listing import (
    PhotoStub,
    iter_unique_authors,
    parse_authors_page,
    parse_nomination_page,
)
from .media import (
    download_avatar,
    download_flag,
    download_photo,
    make_thumb,
    safe_slug,
)
from .photodata import ContestEntry, fetch_photo_data
from .technical import merge_color_facets

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "catalog.json"
ANALYSES_PATH = ROOT / "analysis" / "analyses.json"
CATALOG_DIR = ROOT / "catalog"
WORK_DIR = ROOT / "work"
WIN_BADGE_URL = "https://c1.35photo.pro/photobank/1/7415.png"

BADGE_TIERS = {"win": 4, "best": 3, "top": 2, "stage": 1, "other": 0}


def load_analyses() -> dict[str, Any]:
    if not ANALYSES_PATH.exists():
        return {}
    return json.loads(ANALYSES_PATH.read_text(encoding="utf-8"))


def badge_tier(label: str) -> str:
    value = (label or "").strip().lower()
    if "win" in value:
        return "win"
    if "best of contest" in value:
        return "best"
    if value.startswith("top"):
        return "top"
    if "stage" in value:
        return "stage"
    return "other"



def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_photo_award(
    contests: list[ContestEntry], nomination_name: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    honours: list[dict[str, Any]] = []
    for contest in contests:
        if not contest.badge_label:
            continue
        tier = badge_tier(contest.badge_label)
        contest_key = f"{contest.entity_type}:{contest.contest_id or contest.under_id}"
        honours.append(
            {
                "label": contest.badge_label,
                "kind": tier,
                "tier": tier,
                "contest": contest.under_title or contest.name,
                "contest_key": contest_key,
                "contest_id": contest.contest_id,
                "under_id": contest.under_id,
                "type": contest.entity_type,
                "link": contest.link,
            }
        )

    honours.sort(key=lambda item: BADGE_TIERS.get(item["tier"], 0), reverse=True)
    return (honours[0] if honours else None), honours


def author_cache_path(slug: str) -> Path:
    return WORK_DIR / "authors" / f"{safe_slug(slug)}.json"


def load_author(
    client: HttpClient, stub: PhotoStub, *, refresh: bool = False
) -> AuthorProfile:
    cache_path = author_cache_path(stub.author_slug)
    if cache_path.exists() and not refresh:
        try:
            return AuthorProfile(**json.loads(cache_path.read_text(encoding="utf-8")))
        except (TypeError, ValueError):
            pass

    url = stub.author_url or f"{BASE_URL}/author/{stub.author_slug}/"
    if url.startswith("/"):
        url = BASE_URL + url
    try:
        profile = fetch_author(client, url)
    except Exception:
        # Some old/deleted authors return 410. Keep the listing-level author data.
        profile = AuthorProfile(
            slug=stub.author_slug,
            name=stub.author_name,
            name_native=stub.author_name,
            avatar_url="",
            country=stub.country,
            city=stub.city,
            followers=0,
            following=0,
            photos_count=0,
        )
    if not profile.slug:
        profile.slug = stub.author_slug
    if not profile.name:
        profile.name = stub.author_name
    if not profile.name_native:
        profile.name_native = stub.author_name
    if not profile.country:
        profile.country = stub.country
    if not profile.city:
        profile.city = stub.city
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(profile.__dict__, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return profile


def scrape(
    *,
    nomination_slug: str,
    edition_slug: str,
    limit: int = 35,
    refresh_authors: bool = False,
) -> Path:
    config = load_config()
    nomination = config["nominations"][nomination_slug]
    edition = config["editions"][edition_slug]
    nomination_id = nomination["editions"][edition_slug]

    base = f"{BASE_URL}/{edition['winners_path']}/nomination/{nomination_id}"
    listing_url = f"{base}/"
    photographers_url = f"{base}/photographers/"

    client = HttpClient()
    analyses = load_analyses()

    print(f"→ {listing_url}")
    page = parse_nomination_page(client.get_text(listing_url), limit=limit)
    if not page.photos:
        raise RuntimeError("No photos found on the winners page")

    print(f"→ {photographers_url}")
    members_count, author_cards = parse_authors_page(
        client.get_text(photographers_url)
    )
    ranks = {card.slug: card.rank for card in author_cards}

    edition_dir = CATALOG_DIR / "nominations" / nomination_slug / edition_slug
    full_dir = edition_dir / "photos" / "full"
    thumb_dir = edition_dir / "photos" / "thumb"
    avatar_dir = edition_dir / "avatars"
    flags_dir = CATALOG_DIR / "assets" / "flags"
    badges_dir = CATALOG_DIR / "assets" / "badges"
    for directory in (full_dir, thumb_dir, avatar_dir, flags_dir, badges_dir):
        directory.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    profiles: dict[str, AuthorProfile] = {}

    for stub in page.photos:
        print(
            f"  {stub.rank:02d}/{limit:02d}  photo {stub.photo_id}  "
            f"{stub.author_name or stub.author_slug}"
        )
        photo = fetch_photo_data(client, stub.photo_id, referer=listing_url)

        profile = profiles.get(stub.author_slug)
        if profile is None:
            profile = load_author(client, stub, refresh=refresh_authors)
            profiles[stub.author_slug] = profile

        award, honours = find_photo_award(photo.contests, nomination["name"])
        if stub.rank > 35 and (not award or award["tier"] not in {"win", "best", "top"}):
            print("    skip: outside top-35 and no top award")
            continue

        base_name = (
            f"{stub.rank:02d}_{safe_slug(stub.author_slug or stub.author_name)}"
            f"_{stub.photo_id}"
        )
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
        avatar_url = profile.avatar_url or stub.author_avatar or photo.author_avatar
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
        facets["award"] = sorted(
            {item["tier"] for item in honours if item["tier"] in BADGE_TIERS},
            key=lambda tier: BADGE_TIERS.get(tier, 0),
            reverse=True,
        )
        if stub.rank <= 35:
            facets["award"].append("top35")
        facets["nomination"] = [nomination_slug]
        facets["year"] = [str(edition["year"])]
        facets["source"] = ["nomination"]

        badges: list[str] = []
        if award and award["tier"] == "win":
            badge_path = badges_dir / "100-best-photos.png"
            if not badge_path.exists():
                client.download(WIN_BADGE_URL, badge_path)
            if badge_path.exists():
                badges.append("assets/badges/100-best-photos.png")

        records.append(
            {
                "rank": stub.rank,
                "id": stub.photo_id,
                "title": photo.title or stub.title,
                "description": photo.description or stub.description,
                "page_url": f"{base}/#photo_{stub.photo_id}",
                "source_url": f"{BASE_URL}/gallery/photo/{stub.photo_id}/",
                "top35": stub.rank <= 35,
                "image": {
                    "source": source_url,
                    "full": f"photos/full/{base_name}.jpg" if ok else "",
                    "thumb": f"photos/thumb/{base_name}.jpg"
                    if thumb_path.exists()
                    else "",
                    "width": width,
                    "height": height,
                },
                "award": award,
                "honours": honours,
                "badge_images": badges,
                "analysis": analysis,
                "facets": facets,
                "memberships": [
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
                ],
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
                    "profile_url": stub.author_url
                    or f"{BASE_URL}/author/{stub.author_slug}/",
                    "external_profile": stub.external_profile
                    or next(
                        (
                            url
                            for url in profile.same_as
                            if "35photo.pro" in url
                        ),
                        "",
                    ),
                    "avatar": f"avatars/{avatar_name}"
                    if avatar_path.exists()
                    else "",
                    "country": profile.country or stub.country,
                    "country_code": country_code,
                    "flag": f"assets/flags/{flag_name}"
                    if flag_name
                    else "",
                    "city": profile.city or stub.city,
                    "followers": profile.followers or photo.followers,
                    "following": profile.following,
                    "photos_count": profile.photos_count,
                    "rank_in_nomination": ranks.get(stub.author_slug),
                    "genres": profile.genres,
                    "gear": profile.gear,
                },
            }
        )

    data = {
        "schema_version": 1,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "nomination": {
            "slug": nomination_slug,
            "name": nomination["name"],
            "name_ru": nomination.get("name_ru", ""),
            "description_ru": nomination.get("description_ru", ""),
            "source_url": listing_url,
            "works_count": page.works_count,
            "authors_count": members_count,
        },
        "edition": {
            "slug": edition_slug,
            "year": edition["year"],
            "title": edition["title"],
            "source_url": listing_url,
            "photographers_url": photographers_url,
        },
        "limit": limit,
        "photos": records,
    }

    data_path = edition_dir / "data.json"
    data_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSaved {len(records)} photos → {data_path}")
    return data_path
