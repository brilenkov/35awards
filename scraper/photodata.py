"""Author photo data API: metrics, awards and the full-size image URL."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from .client import BASE_URL, HttpClient


@dataclass
class ContestEntry:
    name: str
    under_title: str
    badge_html: str
    badge_label: str
    link: str
    contest_id: str = ""
    under_id: str = ""
    pcp_id: str = ""
    entity_type: str = "other"


@dataclass
class PhotoData:
    photo_id: int
    title: str
    description: str
    image_url: str
    views: int
    likes: int
    favorites: int
    followers: int
    author_name: str
    author_url: str
    author_avatar: str
    badges: list[str] = field(default_factory=list)
    contests: list[ContestEntry] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _badge_label(html: str) -> str:
    if not html:
        return ""
    if "fa-trophy" in html:
        return "WIN"
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    if text.upper().startswith("TOP"):
        return text
    return text


def fetch_photo_data(
    client: HttpClient,
    photo_id: int,
    *,
    award_id: int = 0,
    referer: str = f"{BASE_URL}/",
) -> PhotoData:
    try:
        payload = client.get_json(
            f"{BASE_URL}/author/photodata/",
            params={"photo_id": photo_id, "award_id": award_id, "return": "text"},
            referer=referer,
        )
    except Exception:
        # Old/deleted works can return 410 or an empty body. The caller still has
        # listing data (image URL, author, title), so return a safe empty record.
        payload = {}

    contests = []
    for item in payload.get("contests") or []:
        link = item.get("link") or ""
        if "/winners" in link and "/nomination/" in link:
            entity_type = "nomination"
        elif "/page/contests/num/" in link:
            entity_type = "theme"
        else:
            entity_type = "other"
        contests.append(
            ContestEntry(
                name=item.get("name") or "",
                under_title=item.get("under_title") or "",
                badge_html=item.get("badge") or "",
                badge_label=_badge_label(item.get("badge") or ""),
                link=link,
                contest_id=str(item.get("contest_id") or ""),
                under_id=str(item.get("under_id") or ""),
                pcp_id=str(item.get("pcp_Id") or ""),
                entity_type=entity_type,
            )
        )

    return PhotoData(
        photo_id=photo_id,
        title=payload.get("photo_title") or "",
        description=payload.get("photo_desc") or "",
        image_url=payload.get("src1500") or "",
        views=_int(payload.get("see")),
        likes=_int(payload.get("likes")),
        favorites=_int(payload.get("fav_count")),
        followers=_int(payload.get("followers")),
        author_name=payload.get("author_name") or "",
        author_url=payload.get("author_link") or "",
        author_avatar=payload.get("author_src") or "",
        badges=list(payload.get("badges") or []),
        contests=contests,
        raw=payload,
    )
