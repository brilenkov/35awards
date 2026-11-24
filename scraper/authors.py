"""Author profile parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from .client import HttpClient


@dataclass
class AuthorProfile:
    slug: str
    name: str
    name_native: str
    avatar_url: str
    country: str
    city: str
    followers: int
    following: int
    photos_count: int
    genres: list[str] = field(default_factory=list)
    gear: list[dict[str, Any]] = field(default_factory=list)
    same_as: list[str] = field(default_factory=list)


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def _int(value: str | None) -> int:
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else 0


def _json_ld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in soup.find_all("script", type="application/ld+json"):
        text = node.string or node.get_text()
        try:
            data = json.loads(text)
        except (TypeError, ValueError):
            continue
        if isinstance(data, dict):
            result.extend(data.get("@graph", [data]))
        elif isinstance(data, list):
            result.extend(item for item in data if isinstance(item, dict))
    return result


def fetch_author(client: HttpClient, url: str) -> AuthorProfile:
    html = client.get_text(url, referer=url)
    soup = BeautifulSoup(html, "lxml")

    slug = ""
    match = re.search(r"/author/([^/?#]+)/?", url)
    if match:
        slug = match.group(1)

    name = _clean(
        soup.select_one(".authorName").get_text(" ", strip=True)
        if soup.select_one(".authorName")
        else ""
    )
    native = _clean(
        soup.select_one(".authorNameNative").get_text(" ", strip=True)
        if soup.select_one(".authorNameNative")
        else ""
    )

    avatar = soup.select_one("img.author-avatar")
    avatar_url = avatar.get("src", "") if avatar else ""

    stats = soup.select(".author-stats a")
    followers = _int(stats[0].get_text(" ", strip=True)) if len(stats) > 0 else 0
    following = _int(stats[1].get_text(" ", strip=True)) if len(stats) > 1 else 0

    locations = soup.select(".author-location a.hometown")
    country = _clean(locations[0].get_text(" ", strip=True)) if locations else ""
    city = _clean(locations[1].get_text(" ", strip=True)) if len(locations) > 1 else ""

    genres = [
        _clean(node.get_text(" ", strip=True))
        for node in soup.select(".user-info .authorThemeTag")
    ]
    genres = [g for g in genres if g]

    gear: list[dict[str, Any]] = []
    for tag in soup.select(".author-equipment .authorGearTag"):
        text = _clean(tag.get_text(" ", strip=True))
        count_el = tag.select_one(".authorGearCount")
        count = _int(count_el.get_text(" ", strip=True)) if count_el else 0
        name_text = text
        if count_el is not None:
            name_text = _clean(text.replace(_clean(count_el.get_text(" ", strip=True)), ""))
        gear.append({"name": name_text, "count": count})

    photos_count = 0
    same_as: list[str] = []
    for data in _json_ld(soup):
        if data.get("@type") == "ItemList":
            photos_count = int(data.get("numberOfItems") or 0)
        if data.get("@type") == "Person":
            same_as = [str(item) for item in data.get("sameAs") or []]

    return AuthorProfile(
        slug=slug,
        name=name,
        name_native=native,
        avatar_url=avatar_url,
        country=country,
        city=city,
        followers=followers,
        following=following,
        photos_count=photos_count,
        genres=genres,
        gear=gear,
        same_as=same_as,
    )
