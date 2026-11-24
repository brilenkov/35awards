"""Parsing of the public winners pages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from bs4 import BeautifulSoup


@dataclass
class PhotoStub:
    rank: int
    photo_id: int
    image_url: str
    author_slug: str
    author_name: str
    author_url: str
    author_avatar: str
    country: str
    country_code: str
    city: str
    award_marker: str = ""
    badge_image: str = ""
    title: str = ""
    description: str = ""
    external_profile: str = ""


@dataclass
class NominationPage:
    title: str
    works_count: str
    photos: list[PhotoStub] = field(default_factory=list)


@dataclass
class AuthorCard:
    rank: int
    slug: str
    name: str
    profile_url: str
    country: str
    city: str


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def _absolute_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://35awards.com" + url
    return url


def _photo_id_from_item(item: "Tag", image_url: str) -> int | None:
    raw = item.get("photo-id")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    link = item.select_one("a[data-sub-html^='#caption']")
    if link is not None:
        match = re.search(r"#caption(\d+)", link.get("data-sub-html", ""))
        if match:
            return int(match.group(1))
    for source in (image_url, item.find("a", href=True).get("href", "") if item.find("a", href=True) else ""):
        match = re.search(r"/(\d+)_(?:500|800|1000|1500)n\.jpg", source or "")
        if not match:
            match = re.search(r"/(\d+)\.(?:jpg|jpeg|png)", source or "")
        if match:
            return int(match.group(1))
    return None


def _slug_from_url(url: str) -> str:
    match = re.search(r"/author/([^/?#]+)/?", url)
    return match.group(1) if match else ""


def parse_nomination_page(html: str, *, limit: int | None = None) -> NominationPage:
    soup = BeautifulSoup(html, "lxml")

    h1 = soup.select_one("h1")
    title = _clean(h1.get_text(" ", strip=True)) if h1 else ""

    works_el = soup.select_one(
        "div[title='Number of photos in the nomination']"
    )
    works_count = _clean(works_el.get_text(" ", strip=True)) if works_el else ""
    if not works_count:
        description = soup.select_one("meta[name='description']")
        if description is not None:
            match = re.search(
                r"([\d.,]+\s?[KM]?)\s+entr(?:y|ies)",
                description.get("content", ""),
                re.IGNORECASE,
            )
            if match:
                works_count = match.group(1).replace(" ", "")

    photos: list[PhotoStub] = []
    seen_ids: set[int] = set()
    items = soup.select("div.parentGenre.openPhoto, div.parentGenre")
    for item in items:
        if limit is not None and len(photos) >= limit:
            break

        image = item.select_one("img.lozadPhoto") or item.select_one("div.genreItemPage img")
        image_url = ""
        if image is not None:
            image_url = image.get("data-src", "") or image.get("src", "")
        if not image_url:
            continue

        photo_id = _photo_id_from_item(item, image_url)
        if photo_id is None or photo_id in seen_ids:
            continue
        seen_ids.add(photo_id)

        badge = item.select_one("div[align='right'] img")
        badge_image = badge.get("src", "") if badge else ""

        author_block = item.find_next_sibling(
            "div", class_=lambda value: value and "authorBlock" in value
        )

        author_url = ""
        author_name = ""
        author_avatar = ""
        country = ""
        country_code = ""
        city = ""
        if author_block is not None:
            links = author_block.select("a[href*='/author/']")
            author_link = next(
                (link for link in links if _clean(link.get_text(" ", strip=True))),
                links[0] if links else None,
            )
            if author_link is not None:
                author_url = _absolute_url(author_link.get("href", ""))
                author_name = _clean(author_link.get_text(" ", strip=True))
            avatar = author_block.select_one("img.avatar")
            if avatar is not None:
                author_avatar = avatar.get("data-src", "") or avatar.get("src", "")
            locations = author_block.select("a.hometown")
            if locations:
                country = _clean(locations[0].get_text(" ", strip=True))
                country_code = _country_code(locations[0].get("href", ""))
            if len(locations) > 1:
                city = _clean(locations[1].get_text(" ", strip=True))

        title_text = ""
        description = ""
        award_marker = ""
        external_profile = ""

        caption = soup.select_one(f"#caption{photo_id}")
        if caption is not None:
            first_p = caption.select_one("p")
            if first_p is not None:
                award_marker = _clean(first_p.get_text(" ", strip=True))
                bold = first_p.select_one("b")
                if bold is not None:
                    title_text = _clean(bold.get_text(" ", strip=True))
                    if title_text:
                        award_marker = award_marker.replace(title_text, "").strip()

            for p in caption.select("p"):
                if p is first_p or p.select_one("i") or p.select_one("a"):
                    continue
                text = _clean(p.get_text(" ", strip=True))
                if text:
                    description = text
                    break

            link = caption.select_one("a[href*='35photo.pro']")
            if link is not None:
                external_profile = link.get("href", "")

            if not author_url:
                link = caption.select_one("a[href*='/author/']")
                if link is not None:
                    author_url = link.get("href", "")
                    author_name = author_name or _clean(
                        link.get_text(" ", strip=True)
                    )

        photos.append(
            PhotoStub(
                rank=len(photos) + 1,
                photo_id=photo_id,
                image_url=image_url,
                author_slug=_slug_from_url(author_url),
                author_name=author_name,
                author_url=author_url,
                author_avatar=author_avatar,
                country=country,
                country_code=country_code,
                city=city,
                award_marker=award_marker,
                badge_image=badge_image,
                title=title_text,
                description=description,
                external_profile=external_profile,
            )
        )

    return NominationPage(title=title, works_count=works_count, photos=photos)


def parse_authors_page(html: str) -> tuple[str, list[AuthorCard]]:
    soup = BeautifulSoup(html, "lxml")
    members_el = soup.select_one(
        "div[title='Number of members in the nomination']"
    )
    # The photographers page renders the counter without a title attribute in
    # some versions; fall back to the text next to the large number.
    members_count = _clean(members_el.get_text(" ", strip=True)) if members_el else ""

    cards: list[AuthorCard] = []
    for col in soup.select("div.col-md-2.col-6"):
        name_link = col.select_one("div.nameOnTop a[href*='/author/']")
        if name_link is None:
            continue
        profile_url = name_link.get("href", "")
        name = _clean(name_link.get_text(" ", strip=True))
        location = col.select_one("div.country_photographers")
        country = ""
        city = ""
        if location is not None:
            links = location.select("a")
            if links:
                country = _clean(links[0].get_text(" ", strip=True))
            if len(links) > 1:
                city = _clean(links[1].get_text(" ", strip=True))
        cards.append(
            AuthorCard(
                rank=len(cards) + 1,
                slug=_slug_from_url(profile_url),
                name=name,
                profile_url=profile_url,
                country=country,
                city=city,
            )
        )

    return members_count, cards


def _country_code(href: str) -> str:
    match = re.search(r"/country/([A-Za-z]{2})/", href)
    return match.group(1).upper() if match else ""


def iter_unique_authors(photos: Iterable[PhotoStub]) -> dict[str, PhotoStub]:
    result: dict[str, PhotoStub] = {}
    for photo in photos:
        if photo.author_slug and photo.author_slug not in result:
            result[photo.author_slug] = photo
    return result
