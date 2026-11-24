"""Parsing of completed thematic contest result pages.

Thematic results use a different grid than the main nominations:
`#loadLozadGrid .grid-item` with `a.openPhoto[photo-id]`, an author link in
`.pl-3`, and a `bestShild`/TOP badge. The main nomination parser does not work
here, so this module keeps the theme-specific logic separate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ThemePhotoStub:
    rank: int
    photo_id: int
    image_url: str
    author_slug: str
    author_name: str
    author_url: str
    award: str = ""
    country: str = ""
    country_code: str = ""
    city: str = ""
    author_avatar: str = ""
    external_profile: str = ""


@dataclass
class ThemeResults:
    title: str
    photos: list[ThemePhotoStub] = field(default_factory=list)


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def parse_theme_results(html: str, *, limit: int | None = None) -> ThemeResults:
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.select_one("h1")
    title = _clean(h1.get_text(" ", strip=True)) if h1 else ""

    grid_nodes = soup.select("#loadLozadGrid")
    if not grid_nodes:
        grid_nodes = [soup]
    photos: list[ThemePhotoStub] = []
    seen: set[str] = set()

    for grid in grid_nodes:
        for item in grid.select(".grid-item"):
            link = item.select_one("a.openPhoto[photo-id]")
            if link is None:
                continue
            photo_id = link.get("photo-id")
            if not photo_id or photo_id in seen:
                continue
            seen.add(photo_id)

            image = item.select_one("img.photo-item")
            image_url = ""
            if image is not None:
                image_url = image.get("data-src", "") or image.get("src", "")
            if not image_url:
                continue

            author_link = item.select_one(".pl-3 a[href*='/author/']")
            author_url = author_link.get("href", "") if author_link else ""
            if author_url.startswith("/"):
                author_url = "https://35awards.com" + author_url
            author_name = (
                _clean(author_link.get_text(" ", strip=True)) if author_link else ""
            )
            match = re.search(r"/author/([^/?#]+)/?", author_url)
            author_slug = match.group(1) if match else ""

            shield = item.select_one(".bestShild")
            award = _clean(shield.get_text(" ", strip=True)) if shield else ""

            photos.append(
                ThemePhotoStub(
                    rank=len(photos) + 1,
                    photo_id=int(photo_id),
                    image_url=image_url,
                    author_slug=author_slug,
                    author_name=author_name,
                    author_url=author_url,
                    award=award,
                )
            )
            if limit is not None and len(photos) >= limit:
                return ThemeResults(title=title, photos=photos)

    return ThemeResults(title=title, photos=photos)
