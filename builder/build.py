"""Build the static catalog HTML from scraped data.json files."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
CATALOG = ROOT / "catalog"
CONFIG_PATH = ROOT / "config" / "catalog.json"
FACETS_PATH = ROOT / "config" / "facets.json"
CONTEST_META_PATH = ROOT / "config" / "contest_meta.json"
ANALYSES_PATH = ROOT / "analysis" / "analyses.json"
ANALYSES: dict[str, Any] = {}


def attach_analysis(item: dict[str, Any]) -> dict[str, Any]:
    analysis = ANALYSES.get(str(item.get("id")))
    if not analysis:
        return item
    item["analysis"] = analysis
    facets = item.setdefault("facets", {})
    for group, values in (analysis.get("facets") or {}).items():
        current = set(facets.get(group) or [])
        current |= set(values)
        facets[group] = sorted(current)
    review = facets.setdefault("review", [])
    if "analysis" not in review:
        review.append("analysis")
    if analysis.get("recipe") and "recipe" not in review:
        review.append("recipe")
    if not analysis.get("auto") and "curated" not in review:
        review.append("curated")
    return item


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def enrich_photo(
    photo: dict[str, Any],
    nomination: dict[str, Any],
    edition: dict[str, Any],
) -> dict[str, Any]:
    """Add page-independent URLs and the nomination/edition context."""
    item = json.loads(json.dumps(photo, ensure_ascii=False))
    slug = nomination["slug"]
    edition_slug = edition["slug"]

    item["nomination"] = {
        "slug": slug,
        "name": nomination["name"],
        "name_ru": nomination.get("name_ru", ""),
    }
    item["nomination_id"] = str(
        (nomination.get("editions") or {}).get(edition_slug) or ""
    )
    item["edition"] = {
        "slug": edition_slug,
        "year": edition["year"],
        "title": edition["title"],
    }
    item["entity_type"] = "nomination"

    image = item.get("image") or {}
    thumb = image.get("thumb") or ""
    full = image.get("full") or ""
    image["thumb_url"] = f"nominations/{slug}/{edition_slug}/{thumb}" if thumb else ""
    image["full_url"] = f"nominations/{slug}/{edition_slug}/{full}" if full else ""

    author = item.get("author") or {}
    avatar = author.get("avatar") or ""
    author["avatar_url"] = (
        f"nominations/{slug}/{edition_slug}/{avatar}" if avatar else ""
    )
    item["badge_urls"] = list(item.get("badge_images") or [])
    return attach_analysis(item)


def enrich_theme_photo(photo: dict[str, Any], theme: dict[str, Any]) -> dict[str, Any]:
    item = json.loads(json.dumps(photo, ensure_ascii=False))
    slug = theme["slug"]
    contest_id = str(theme["contest_id"])

    item["nomination"] = {
        "slug": slug,
        "name": theme["title"],
        "name_ru": theme.get("name_ru", ""),
    }
    item["edition"] = {
        "slug": contest_id,
        "year": theme.get("year"),
        "title": "Тематический конкурс",
    }
    item["theme"] = {
        "slug": slug,
        "title": theme["title"],
        "name_ru": theme.get("name_ru", ""),
        "contest_id": theme["contest_id"],
        "year": theme.get("year"),
        "category": theme.get("category", ""),
    }
    item["entity_type"] = "theme"

    image = item.get("image") or {}
    thumb = image.get("thumb") or ""
    full = image.get("full") or ""
    image["thumb_url"] = f"themes/{slug}/{contest_id}/{thumb}" if thumb else ""
    image["full_url"] = f"themes/{slug}/{contest_id}/{full}" if full else ""

    author = item.get("author") or {}
    avatar = author.get("avatar") or ""
    author["avatar_url"] = f"themes/{slug}/{contest_id}/{avatar}" if avatar else ""
    item["badge_urls"] = list(item.get("badge_images") or [])
    return attach_analysis(item)


def badge_tier(label: str) -> str:
    value = (label or "").lower()
    if "win" in value:
        return "win"
    if "best of contest" in value:
        return "best"
    if value.startswith("top"):
        return "top"
    if "stage" in value:
        return "stage"
    return "other"


def badge_percent(label: str) -> float:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", label or "")
    if not match:
        return 999.0
    return float(match.group(1).replace(",", "."))


def award_priority(membership: dict[str, Any]) -> tuple[int, float]:
    tier = badge_tier(membership.get("badge", ""))
    order = {"win": 4, "best": 3, "top": 2, "stage": 1}
    percent = badge_percent(membership.get("badge", "")) if tier == "top" else 999.0
    return order.get(tier, 0), -percent


def contest_key_for(item: dict[str, Any]) -> str:
    if item.get("type") == "theme":
        return f"theme:{item.get('contest_id') or item.get('under_id')}"
    if item.get("type") == "nomination":
        return f"nomination:{item.get('under_id') or item.get('contest_id')}"
    return ""


def apply_memberships(
    item: dict[str, Any],
    theme_by_contest_id: dict[str, dict[str, Any]],
    nomination_by_id: dict[str, str],
) -> dict[str, Any]:
    """Enrich a photo with all nomination/theme memberships and filter facets."""
    memberships = item.get("memberships") or []
    facets = item.setdefault("facets", {})
    sources = set(facets.get("source") or [])
    themes = set(facets.get("theme") or [])
    nominations = set(facets.get("nomination") or [])
    years = set(facets.get("year") or [])
    awards = set(facets.get("award") or [])
    contests = set(facets.get("contest") or [])
    source_nomination_id = str(item.get("nomination_id") or "")
    if source_nomination_id:
        contests.add(f"nomination:{source_nomination_id}")

    for membership in memberships:
        contest_id = str(membership.get("contest_id") or "")
        under_id = str(membership.get("under_id") or "")
        tier = badge_tier(membership.get("badge", ""))
        if tier in {"win", "best", "top", "stage"}:
            awards.add(tier)
        membership["contest_key"] = contest_key_for(membership)
        if membership.get("type") == "theme":
            if contest_id:
                contests.add(f"theme:{contest_id}")
            theme = theme_by_contest_id.get(contest_id)
            if theme:
                themes.add(theme["slug"])
                sources.add("theme")
                if theme.get("year"):
                    years.add(str(theme["year"]))
        elif membership.get("type") == "nomination":
            if under_id:
                contests.add(f"nomination:{under_id}")
            slug = nomination_by_id.get(under_id)
            if slug:
                nominations.add(slug)
                sources.add("nomination")

    facets["source"] = sorted(sources) or ["nomination"]
    facets["theme"] = sorted(themes)
    facets["nomination"] = sorted(nominations)
    facets["year"] = sorted(years)
    facets["contest"] = sorted(contests)
    facets["award"] = sorted(awards, key=lambda value: {"win": 4, "best": 3, "top": 2, "stage": 1}.get(value, 0), reverse=True)

    theme_items = [theme_by_contest_id[t] for t in facets["theme"] if t in theme_by_contest_id]
    item["themes"] = [
        {
            "slug": theme["slug"],
            "title": theme["title"],
            "name_ru": theme.get("name_ru", ""),
            "contest_id": theme["contest_id"],
            "year": theme.get("year"),
            "category": theme.get("category", ""),
        }
        for theme in theme_items
    ]

    unique_memberships = {
        (m.get("type"), str(m.get("contest_id") or ""), str(m.get("under_id") or ""))
        for m in memberships
        if m.get("type") in {"nomination", "theme"} and (m.get("contest_id") or m.get("under_id"))
    }
    top_awards = {
        (m.get("type"), str(m.get("contest_id") or ""), str(m.get("under_id") or ""))
        for m in memberships
        if badge_tier(m.get("badge", "")) in {"win", "best", "top"}
    }
    nomination_memberships = {
        str(m.get("under_id") or "")
        for m in memberships
        if m.get("type") == "nomination" and m.get("under_id")
    }
    theme_memberships = {
        str(m.get("contest_id") or "")
        for m in memberships
        if m.get("type") == "theme" and m.get("contest_id")
    }
    multi = []
    if len(unique_memberships) >= 2:
        multi.append("multi")
    if len(unique_memberships) >= 3:
        multi.append("contests_3")
    if len(unique_memberships) >= 4:
        multi.append("contests_4")
    if len(top_awards) >= 2:
        multi.append("multi_award")
    if len(top_awards) >= 3:
        multi.append("awards_3")
    if len(top_awards) >= 4:
        multi.append("awards_4")
    if len(nomination_memberships) >= 2:
        multi.append("multi_nomination")
    if len(theme_memberships) >= 2:
        multi.append("multi_theme")
    facets["multi"] = multi
    item["multi"] = {
        "memberships": len(unique_memberships),
        "top_awards": len(top_awards),
        "nominations": len(nomination_memberships),
        "themes": len(theme_memberships),
        "score": len(unique_memberships) * 2
        + len(top_awards) * 5
        + len(nomination_memberships) * 3
        + len(theme_memberships),
    }
    return item


def enrich_contest_meta(
    photo: dict[str, Any], contest_meta: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Attach human names and years to memberships and honours."""
    memberships = photo.get("memberships") or []
    for membership in memberships:
        key = membership.get("contest_key") or contest_key_for(membership)
        membership["contest_key"] = key
        meta = contest_meta.get(key)
        if meta:
            membership["title"] = meta.get("title") or membership.get("name")
            membership["year"] = meta.get("year")
    for honour in photo.get("honours") or []:
        key = contest_key_for(honour) or honour.get("contest_key")
        honour["contest_key"] = key
        meta = contest_meta.get(key) if key else None
        if meta:
            honour["contest"] = meta.get("title") or honour.get("contest")
            honour["year"] = meta.get("year")

    # A theme work often has no single "source" award, but its memberships can
    # still contain TOP 1% / BEST OF CONTEST. Show the strongest one on the
    # card instead of a generic "ТОП-10" rank fallback.
    if not photo.get("award"):
        candidates = [
            membership
            for membership in memberships
            if badge_tier(membership.get("badge", "")) in {"win", "best", "top", "stage"}
        ]
        if candidates:
            best = max(candidates, key=award_priority)
            badge = best.get("badge") or ""
            title = best.get("title") or best.get("name") or ""
            year = best.get("year")
            parts = [badge]
            if title and title not in badge:
                parts.append(title)
            if year and str(year) not in title:
                parts.append(str(year))
            photo["display_award"] = badge
            photo["display_award_tier"] = badge_tier(badge)
            photo["display_award_title"] = " · ".join(part for part in parts if part)
    return photo


def merge_photo(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Merge the same photo discovered via a nomination and a theme."""
    merged = json.loads(json.dumps(base, ensure_ascii=False))
    facets = merged.setdefault("facets", {})
    extra_facets = extra.get("facets") or {}

    for group in ("source", "theme", "nomination", "year", "multi", "award"):
        values = set(facets.get(group) or []) | set(extra_facets.get(group) or [])
        facets[group] = sorted(values)
    for group in ("contest",):
        values = set(facets.get(group) or []) | set(extra_facets.get(group) or [])
        facets[group] = sorted(values)

    memberships = []
    seen = set()
    for membership in (merged.get("memberships") or []) + (extra.get("memberships") or []):
        key = (
            membership.get("type"),
            str(membership.get("contest_id") or ""),
            str(membership.get("under_id") or ""),
            membership.get("badge"),
        )
        if key in seen:
            continue
        seen.add(key)
        memberships.append(membership)
    merged["memberships"] = memberships

    themes = {t["slug"]: t for t in merged.get("themes") or []}
    for theme in extra.get("themes") or []:
        themes[theme["slug"]] = theme
    merged["themes"] = list(themes.values())

    if not merged.get("analysis") and extra.get("analysis"):
        merged["analysis"] = extra["analysis"]
    merged["entity_type"] = "mixed"
    merged["multi"] = {
        "memberships": max(
            (merged.get("multi") or {}).get("memberships", 0),
            (extra.get("multi") or {}).get("memberships", 0),
        ),
        "top_awards": max(
            (merged.get("multi") or {}).get("top_awards", 0),
            (extra.get("multi") or {}).get("top_awards", 0),
        ),
        "nominations": max(
            (merged.get("multi") or {}).get("nominations", 0),
            (extra.get("multi") or {}).get("nominations", 0),
        ),
        "themes": max(
            (merged.get("multi") or {}).get("themes", 0),
            (extra.get("multi") or {}).get("themes", 0),
        ),
    }
    return merged


def russian_count(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def edition_label(value: str) -> str:
    match = re.search(r"\d+", value or "")
    return f"{match.group(0)}-й конкурс" if match else value


def plural(value: int, one: str, few: str, many: str) -> str:
    number = abs(int(value or 0)) % 100
    if 11 <= number <= 19:
        return many
    number %= 10
    if number == 1:
        return one
    if 2 <= number <= 4:
        return few
    return many


def ru_date(value: str) -> str:
    try:
        year, month, day = value.split("-")
        return f"{day}.{month}.{year}"
    except (AttributeError, ValueError):
        return value


def discover(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return nomination slug -> edition slug -> data."""
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(CATALOG.glob("nominations/*/*/data.json")):
        data = load_json(path)
        nomination_slug = data["nomination"]["slug"]
        edition_slug = data["edition"]["slug"]
        result.setdefault(nomination_slug, {})[edition_slug] = data

    # Keep the configured nomination order and add any extra scraped ones.
    ordered: dict[str, dict[str, Any]] = {}
    for slug in config["nominations"]:
        if slug in result:
            ordered[slug] = result[slug]
    for slug, editions in result.items():
        ordered.setdefault(slug, editions)
    return ordered


def nomination_meta(config: dict[str, Any], slug: str, editions: dict[str, Any]) -> dict[str, Any]:
    configured = config["nominations"].get(slug, {})
    latest = max(editions.values(), key=lambda item: item["edition"]["year"])
    return {
        "slug": slug,
        "name": configured.get("name") or latest["nomination"]["name"],
        "name_ru": configured.get("name_ru") or latest["nomination"]["name_ru"],
        "description_ru": configured.get("description_ru")
        or latest["nomination"].get("description_ru", ""),
        "works_count": latest["nomination"].get("works_count", ""),
        "editions": configured.get("editions", {}),
    }


def discover_themes(config: dict[str, Any]) -> list[dict[str, Any]]:
    themes: list[dict[str, Any]] = []
    for path in sorted(CATALOG.glob("themes/*/*/data.json")):
        data = load_json(path)
        theme = data.get("theme") or {}
        if not theme.get("slug"):
            continue
        configured = config.get("themes", {}).get(theme["slug"], {})
        theme = {**configured, **theme}
        theme["slug"] = theme["slug"]
        theme["photo_count"] = len(data.get("photos") or [])
        theme["_data"] = data
        themes.append(theme)
    order = {slug: index for index, slug in enumerate(config.get("themes", {}))}
    themes.sort(key=lambda item: order.get(item["slug"], 999))
    return themes


def theme_meta(theme: dict[str, Any]) -> dict[str, Any]:
    category = theme.get("category") or ""
    category_labels = {
        "reportage": "Репортаж",
        "nude": "Ню",
        "event": "Мероприятия",
        "color": "Цвет",
        "portrait": "Портрет",
        "light": "Свет",
        "monochrome": "Ч/Б",
    }
    return {
        "slug": theme["slug"],
        "title": theme.get("title") or "",
        "name_ru": theme.get("name_ru") or "",
        "contest_id": theme.get("contest_id"),
        "year": theme.get("year"),
        "category": category,
        "category_label": category_labels.get(category, category),
        "description_ru": theme.get("description_ru") or "",
        "source_url": theme.get("source_url") or theme.get("url") or "",
        "photo_count": theme.get("photo_count", 0),
        "selection": theme.get("selection", "best_of_contest"),
        "selection_label": theme.get("selection_label", "BEST OF CONTEST"),
    }


def build() -> None:
    global ANALYSES
    config = load_json(CONFIG_PATH)
    facets = load_json(FACETS_PATH)
    ANALYSES = load_json(ANALYSES_PATH) if ANALYSES_PATH.exists() else {}
    contest_meta = (
        load_json(CONTEST_META_PATH) if CONTEST_META_PATH.exists() else {}
    )
    nominations_data = discover(config)
    themes_data = discover_themes(config)
    built_at = date.today().isoformat()

    theme_by_contest_id = {
        str(theme["contest_id"]): theme_meta(theme) for theme in themes_data
    }
    nomination_by_id: dict[str, str] = {}
    for slug, editions in nominations_data.items():
        configured = config.get("nominations", {}).get(slug, {}).get("editions", {})
        for edition_slug, nomination_id in configured.items():
            if edition_slug in editions:
                nomination_by_id[str(nomination_id)] = slug

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = russian_count
    env.filters["edition_label"] = edition_label
    env.filters["plural"] = plural
    env.filters["ru_date"] = ru_date

    base_context = {"site": config["site"], "built_at": built_at}

    # ---------------------------------------------------------------- root data
    nominations: list[dict[str, Any]] = []
    nomination_photos: list[dict[str, Any]] = []
    theme_cards: list[dict[str, Any]] = []
    theme_photos: list[dict[str, Any]] = []
    author_slugs: set[str] = set()
    edition_slugs: set[str] = set()

    for slug, editions in nominations_data.items():
        meta = nomination_meta(config, slug, editions)
        ordered_editions = sorted(
            editions.values(), key=lambda item: item["edition"]["year"], reverse=True
        )
        latest = ordered_editions[0]
        photo_count = sum(len(item["photos"]) for item in ordered_editions)
        edition_slugs.update(item["edition"]["slug"] for item in ordered_editions)

        for item in ordered_editions:
            for photo in item["photos"]:
                enriched = apply_memberships(
                    enrich_photo(photo, meta, item["edition"]),
                    theme_by_contest_id,
                    nomination_by_id,
                )
                nomination_photos.append(enriched)
                author_slugs.add(photo["author"]["slug"])

        cover = None
        if latest["photos"]:
            cover = apply_memberships(
                enrich_photo(latest["photos"][0], meta, latest["edition"]),
                theme_by_contest_id,
                nomination_by_id,
            )
        nominations.append(
            {
                **meta,
                "photo_count": photo_count,
                "year_range": (
                    str(latest["edition"]["year"])
                    if len(ordered_editions) == 1
                    else f"{min(item['edition']['year'] for item in ordered_editions)}–{max(item['edition']['year'] for item in ordered_editions)}"
                ),
                "cover": cover,
                "cover_edition": latest["edition"]["slug"],
                "editions": ordered_editions,
            }
        )

    for theme in themes_data:
        meta = theme_meta(theme)
        data = theme["_data"]
        photos = []
        for photo in data.get("photos") or []:
            enriched = apply_memberships(
                enrich_theme_photo(photo, meta),
                theme_by_contest_id,
                nomination_by_id,
            )
            photos.append(enriched)
            theme_photos.append(enriched)
            author_slugs.add(photo["author"]["slug"])
        theme_cards.append(
            {
                **meta,
                "cover": photos[0] if photos else None,
                "catalog_url": f"../../index.html?theme={meta['slug']}#catalog",
            }
        )

    # Deduplicate the same photo when it is both a nomination finalist and a theme winner.
    by_id: dict[str, dict[str, Any]] = {}
    for photo in nomination_photos + theme_photos:
        key = str(photo["id"])
        if key in by_id:
            by_id[key] = merge_photo(by_id[key], photo)
        else:
            by_id[key] = photo
    all_photos = [
        enrich_contest_meta(
            apply_memberships(photo, theme_by_contest_id, nomination_by_id),
            contest_meta,
        )
        for photo in by_id.values()
    ]
    nomination_order = {
        slug: index for index, slug in enumerate(config.get("nominations", {}))
    }
    theme_order = {slug: index for index, slug in enumerate(config.get("themes", {}))}
    all_photos.sort(
        key=lambda photo: (
            0 if photo.get("entity_type") in {"nomination", "mixed"} else 1,
            nomination_order.get(photo.get("nomination", {}).get("slug"), 999)
            if photo.get("entity_type") in {"nomination", "mixed"}
            else 1000 + theme_order.get(photo.get("nomination", {}).get("slug"), 999),
            -(photo.get("edition", {}).get("year") or 0),
            photo.get("rank") or 999,
        )
    )

    # -------------------------------------------------------------- facet counts
    facet_counts: dict[str, dict[str, int]] = {}
    for group in ("source", "nomination", "theme", "year", "award", "multi", "contest"):
        facet_counts[group] = {}
    for group in ("light", "color", "technique", "image", "emotion", "season", "focal", "review"):
        facet_counts[group] = {}
    for photo in all_photos:
        for group, values in (photo.get("facets") or {}).items():
            if group not in facet_counts:
                continue
            for value in values:
                facet_counts[group][value] = facet_counts[group].get(value, 0) + 1

    filter_nominations = []
    for slug in config["nominations"]:
        count = facet_counts["nomination"].get(slug, 0)
        if count == 0 and slug not in nominations_data:
            continue
        meta = nomination_meta(config, slug, nominations_data.get(slug, {})) if slug in nominations_data else {
            "slug": slug,
            "name": config["nominations"][slug]["name"],
            "name_ru": config["nominations"][slug].get("name_ru", ""),
        }
        filter_nominations.append(
            {
                "slug": slug,
                "name": meta["name"],
                "name_ru": meta["name_ru"] or meta["name"],
                "count": count,
            }
        )

    filter_themes = [
        {
            "slug": theme["slug"],
            "title": theme["title"],
            "name_ru": theme.get("name_ru", ""),
            "count": facet_counts["theme"].get(theme["slug"], 0),
            "year": theme.get("year"),
            "contest_id": theme.get("contest_id"),
            "category": theme.get("category", ""),
        }
        for theme in theme_cards
    ]
    filter_years = [
        {"value": year, "label": year, "count": count}
        for year, count in sorted(
            facet_counts["year"].items(), key=lambda pair: pair[0], reverse=True
        )
    ]
    filter_sources = [
        {"value": key, "label": label, "count": facet_counts["source"].get(key, 0)}
        for key, label in facets.get("source", {}).get("options", {}).items()
    ]
    filter_multi = [
        {"value": key, "label": label, "count": facet_counts["multi"].get(key, 0)}
        for key, label in facets.get("multi", {}).get("options", {}).items()
    ]
    filter_contexts = []
    contest_labels: dict[str, str] = {}
    context_photo_ids: dict[str, set] = {}
    for photo in all_photos:
        for key in (photo.get("facets") or {}).get("contest") or []:
            context_photo_ids.setdefault(key, set()).add(photo.get("id"))
    for key, count in facet_counts["contest"].items():
        if not count:
            continue
        meta = contest_meta.get(key, {})
        title = meta.get("title") or key
        year = meta.get("year")
        context_type = meta.get("type") or key.split(":", 1)[0]
        label = f"{title} · {year}" if year else title
        option_label = f"{year} · {title} ({count})" if year else f"{title} ({count})"
        contest_labels[key] = label
        filter_contexts.append(
            {
                "key": key,
                "label": label,
                "option_label": option_label,
                "title": title,
                "year": year,
                "type": context_type,
                "count": count,
            }
        )
    filter_contexts.sort(
        key=lambda item: (
            0 if item["type"] == "nomination" else 1,
            -(item["year"] or 0),
            item["title"],
        )
    )

    # Nominations are grouped into one optgroup per name, with years inside.
    # Every group has an "all years" option that expands to all its contest keys.
    nomination_groups: dict[str, dict[str, Any]] = {}
    theme_contexts = []
    for item in filter_contexts:
        if item["type"] == "nomination":
            group = nomination_groups.setdefault(
                item["title"],
                {
                    "key": f"group:nomination:{item['title']}",
                    "type": "nomination",
                    "title": item["title"],
                    "contexts": [],
                    "photo_ids": set(),
                },
            )
            group["contexts"].append(item)
            group["photo_ids"] |= context_photo_ids.get(item["key"], set())
        else:
            theme_contexts.append(item)

    for group in nomination_groups.values():
        group["contexts"].sort(
            key=lambda item: (-(item["year"] or 0), item["title"])
        )
        group["key_list"] = [item["key"] for item in group["contexts"]]
        group["count"] = len(group["photo_ids"])
        years = [item["year"] for item in group["contexts"] if item["year"]]
        group["latest_year"] = max(years) if years else 0
    filter_context_nominations = sorted(
        nomination_groups.values(),
        key=lambda group: (-group["latest_year"], group["title"]),
    )

    theme_contexts.sort(
        key=lambda item: (-(item["year"] or 0), item["title"])
    )
    multi_count = sum(
        1 for photo in all_photos if (photo.get("multi") or {}).get("memberships", 0) >= 2
    )
    multi_award_count = sum(
        1 for photo in all_photos if (photo.get("multi") or {}).get("top_awards", 0) >= 2
    )

    root_html = env.get_template("index.html").render(
        **base_context,
        nominations=nominations,
        themes=theme_cards,
        photos=all_photos,
        facets=facets,
        filter_nominations=filter_nominations,
        filter_themes=filter_themes,
        filter_years=filter_years,
        filter_sources=filter_sources,
        filter_multi=filter_multi,
        filter_contexts=filter_contexts,
        filter_context_nominations=filter_context_nominations,
        filter_context_themes=theme_contexts,
        facet_counts=facet_counts,
        multi_count=multi_count,
        multi_award_count=multi_award_count,
        stats={
            "nominations": len(nominations),
            "editions": len(edition_slugs),
            "themes": len(theme_cards),
            "photos": len(all_photos),
            "authors": len(author_slugs),
        },
        page_data={"photos": all_photos, "contest_labels": contest_labels},
        asset_prefix="assets/",
        root_prefix="",
        media_base="",
    )
    (CATALOG / "index.html").write_text(root_html, encoding="utf-8")
    print(f"built {CATALOG / 'index.html'}")

    # ---------------------------------------------------------- nomination pages
    for slug, editions in nominations_data.items():
        meta = nomination_meta(config, slug, editions)
        ordered_editions = sorted(
            editions.values(), key=lambda item: item["edition"]["year"], reverse=True
        )
        latest = ordered_editions[0]

        edition_cards: list[dict[str, Any]] = []
        author_map: dict[str, dict[str, Any]] = {}
        nomination_photos: list[dict[str, Any]] = []
        year_counts: dict[str, int] = {}
        for item in ordered_editions:
            cover = item["photos"][0] if item["photos"] else None
            author_slugs = {photo["author"]["slug"] for photo in item["photos"]}
            year = str(item["edition"]["year"])
            year_counts[year] = year_counts.get(year, 0) + len(item["photos"])
            edition_cards.append(
                {
                    "slug": item["edition"]["slug"],
                    "year": item["edition"]["year"],
                    "title": item["edition"]["title"],
                    "photo_count": len(item["photos"]),
                    "authors_count": len(author_slugs),
                    "works_count": item["nomination"].get("works_count", ""),
                    "cover": cover,
                }
            )

            for photo in item["photos"]:
                enriched = enrich_contest_meta(
                    apply_memberships(
                        enrich_photo(photo, meta, item["edition"]),
                        theme_by_contest_id,
                        nomination_by_id,
                    ),
                    contest_meta,
                )
                nomination_photos.append(enriched)
                author = dict(photo["author"])
                key = author["slug"]
                existing = author_map.get(key)
                rank = author.get("rank_in_nomination")
                if existing is None or (rank and not existing["author"].get("rank_in_nomination")):
                    author_map[key] = {
                        "author": author,
                        "edition_slug": item["edition"]["slug"],
                    }

        authors = sorted(
            author_map.values(),
            key=lambda entry: (
                entry["author"].get("rank_in_nomination") is None,
                entry["author"].get("rank_in_nomination") or 10**9,
                entry["author"].get("name", ""),
            ),
        )

        photo_count = len(nomination_photos)
        cover = latest["photos"][0] if latest["photos"] else None
        years = [
            {"value": year, "label": year, "count": count}
            for year, count in sorted(year_counts.items(), key=lambda pair: pair[0], reverse=True)
        ]
        years_sorted = sorted(year_counts.keys())
        year_range = (
            years_sorted[0]
            if len(years_sorted) == 1
            else f"{years_sorted[0]}–{years_sorted[-1]}"
        )
        nomination_page = {
            **meta,
            "photo_count": photo_count,
            "cover": cover,
            "cover_edition": latest["edition"]["slug"],
            "year_range": year_range,
            "catalog_url": f"../../index.html?nomination={slug}#catalog",
        }

        html = env.get_template("nomination.html").render(
            **base_context,
            nomination=nomination_page,
            editions=edition_cards,
            photos=nomination_photos,
            years=years,
            authors=authors[:12],
            page_data={"photos": nomination_photos},
            asset_prefix="../../assets/",
            root_prefix="../../",
            media_base="",
        )
        output = CATALOG / "nominations" / slug / "index.html"
        output.write_text(html, encoding="utf-8")
        print(f"built {output}")

        # ------------------------------------------------------------ edition pages
        for item in ordered_editions:
            edition_slug = item["edition"]["slug"]
            photos = [
                enrich_contest_meta(
                    apply_memberships(
                        enrich_photo(photo, meta, item["edition"]),
                        theme_by_contest_id,
                        nomination_by_id,
                    ),
                    contest_meta,
                )
                for photo in item["photos"]
            ]
            win_count = sum(
                1
                for photo in photos
                if photo.get("award") and photo["award"].get("tier") == "win"
            )
            best_count = sum(
                1
                for photo in photos
                if photo.get("award") and photo["award"].get("tier") == "best"
            )
            top_count = sum(
                1
                for photo in photos
                if photo.get("award") and photo["award"].get("tier") == "top"
            )
            page_data = {"photos": photos}
            html = env.get_template("edition.html").render(
                **base_context,
                nomination=item["nomination"],
                edition=item["edition"],
                photos=photos,
                win_count=win_count,
                best_count=best_count,
                top_count=top_count,
                page_data=page_data,
                asset_prefix="../../../assets/",
                root_prefix="../../../",
                media_base="",
            )
            output = CATALOG / "nominations" / slug / edition_slug / "index.html"
            output.write_text(html, encoding="utf-8")
            print(f"built {output}")

    # -------------------------------------------------------------- theme pages
    for theme in themes_data:
        meta = theme_meta(theme)
        data = theme["_data"]
        photos = [
            enrich_contest_meta(
                apply_memberships(
                    enrich_theme_photo(photo, meta),
                    theme_by_contest_id,
                    nomination_by_id,
                ),
                contest_meta,
            )
            for photo in data.get("photos") or []
        ]
        html = env.get_template("theme.html").render(
            **base_context,
            theme=meta,
            photos=photos,
            page_data={"photos": photos},
            asset_prefix="../../../assets/",
            root_prefix="../../../",
            media_base="",
        )
        output = CATALOG / "themes" / theme["slug"] / str(theme["contest_id"]) / "index.html"
        output.write_text(html, encoding="utf-8")
        print(f"built {output}")

    # ---------------------------------------------------------------- multi page
    multi_photos = [
        photo
        for photo in all_photos
        if (photo.get("multi") or {}).get("top_awards", 0) >= 2
        or (photo.get("multi") or {}).get("memberships", 0) >= 2
    ]
    multi_photos.sort(
        key=lambda photo: (
            -(photo.get("multi") or {}).get("score", 0),
            -(photo.get("multi") or {}).get("top_awards", 0),
            -(photo.get("multi") or {}).get("memberships", 0),
            photo.get("rank") or 999,
        )
    )
    html = env.get_template("multi.html").render(
        **base_context,
        photos=multi_photos,
        asset_prefix="../assets/",
        root_prefix="../",
        media_base="",
    )
    output = CATALOG / "multi" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(f"built {output}")

    # --------------------------------------------------------------- reviews page
    review_photos = [
        photo
        for photo in all_photos
        if photo.get("analysis")
        and (
            not (photo.get("analysis") or {}).get("auto")
            or (photo.get("analysis") or {}).get("recipe")
        )
    ]
    for photo in review_photos:
        if photo.get("entity_type") == "theme" and photo.get("theme"):
            theme = photo["theme"]
            photo["detail_url"] = (
                f"themes/{theme['slug']}/{theme['contest_id']}/index.html"
                f"#photo_{photo['id']}"
            )
        else:
            photo["detail_url"] = (
                f"nominations/{photo['nomination']['slug']}/"
                f"{photo['edition']['slug']}/index.html#photo_{photo['id']}"
            )
    review_photos.sort(
        key=lambda photo: (
            0 if (photo.get("analysis") or {}).get("recipe") else 1,
            -int((photo.get("edition") or {}).get("year") or 0),
            photo.get("rank") or 999,
        )
    )
    recipe_count = sum(
        1 for photo in review_photos if (photo.get("analysis") or {}).get("recipe")
    )
    html = env.get_template("reviews.html").render(
        **base_context,
        photos=review_photos,
        recipe_count=recipe_count,
        total_analyzed=sum(1 for photo in all_photos if photo.get("analysis")),
        asset_prefix="../assets/",
        root_prefix="../",
        media_base="",
    )
    output = CATALOG / "reviews" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(f"built {output}")


def main() -> int:
    global CATALOG
    parser = argparse.ArgumentParser(description="Build the static 35AWARDS catalog")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=CATALOG,
        help="catalog directory (default: ./catalog)",
    )
    args = parser.parse_args()
    CATALOG = args.catalog.resolve()
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
