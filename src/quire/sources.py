from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Callable

import requests
from bs4 import BeautifulSoup

from quire.config import Source

if TYPE_CHECKING:
    from quire.config import Config

USER_AGENT = "quire/0.1 (+https://github.com/alanlaird/quire)"


@dataclass(frozen=True)
class Book:
    title: str
    author: str
    hardcover_book_id: int | None = field(default=None, compare=False, hash=False)


Extractor = Callable[[str], list[Book]]
_REGISTRY: dict[str, Extractor] = {}


def register(kind: str) -> Callable[[Extractor], Extractor]:
    def decorator(fn: Extractor) -> Extractor:
        _REGISTRY[kind] = fn
        return fn
    return decorator


def fetch(source: Source, config: "Config", year: int | None = None) -> list[Book]:
    if source.kind == "hardcover_list":
        import quire.hardcover as hc
        if config.hardcover is None:
            raise ValueError("hardcover_list source requires [hardcover] config section")
        if source.list_id is None:
            raise ValueError(f"source {source.name!r} is missing list_id")
        entries = hc.get_list_books(config.hardcover.api_key, source.list_id)
        return [
            Book(title=e["title"], author=e["author"], hardcover_book_id=e["book_id"])
            for e in entries
        ]
    if source.kind not in _REGISTRY:
        raise ValueError(f"unknown source kind: {source.kind!r}")
    if source.url_template is None:
        raise ValueError(f"source {source.name!r} is missing url_template")
    url = source.url_template.format(year=year if year is not None else _default_year())
    html = _http_get(url)
    return _REGISTRY[source.kind](html)


def _default_year() -> int:
    today = date.today()
    return today.year if today.month >= 11 else today.year - 1


def _ws(s: str) -> str:
    return " ".join(s.split())


def _http_get(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


@register("nebula_nominees")
def _nebula_nominees(html: str) -> list[Book]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(
        lambda t: t.name == "h4" and t.find("a", href=lambda h: h and "best-novel" in h)
    )
    if not heading:
        return []
    ul = heading.find_next_sibling("ul")
    if not ul:
        return []
    books: list[Book] = []
    seen: set[tuple[str, str]] = set()
    for li in ul.find_all("li"):
        # Each li: <a href="..."><em>Title, by Author (Publisher)</em></a>
        em = li.find("em") or li.find("i", class_=False)
        if em is None:
            a = li.find("a")
            text = _ws(a.get_text()) if a else ""
        else:
            text = _ws(em.get_text())
        if ", by " not in text:
            continue
        title_part, _, author_part = text.partition(", by ")
        title = _ws(title_part)
        author = _ws(re.sub(r"\s*\(.*?\)\s*$", "", author_part).rstrip(";").strip())
        if not title or not author:
            continue
        key = (title.lower(), author.lower())
        if key not in seen:
            seen.add(key)
            books.append(Book(title=title, author=author))
    return books


@register("hugo_nominees")
def _hugo_nominees(html: str) -> list[Book]:
    soup = BeautifulSoup(html, "html.parser")
    heading = None
    for tag in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
        if "Best Novel" in tag.get_text():
            heading = tag
            break
    if not heading:
        return []
    ul = heading.find_next("ul")
    if not ul:
        return []
    books: list[Book] = []
    seen: set[tuple[str, str]] = set()
    for li in ul.find_all("li"):
        em = li.find("em") or li.find("i")
        if not em:
            continue
        title = _ws(em.get_text())
        rest = li.get_text()
        idx = rest.find(title)
        after = rest[idx + len(title):] if idx != -1 else rest
        if " by " not in after:
            continue
        author_part = after.split(" by ", 1)[1]
        author = _ws(re.sub(r"\(.*?\)", "", author_part).strip().rstrip(","))
        if not title or not author:
            continue
        key = (title.lower(), author.lower())
        if key not in seen:
            seen.add(key)
            books.append(Book(title=title, author=author))
    return books


@register("goodreads_choice_awards")
def _goodreads_choice_awards(html: str) -> list[Book]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[tuple[str, str]] = set()
    books: list[Book] = []
    for anchor in soup.select('a[href*="/book/show/"][href*="from_choice=true"]'):
        img = anchor.find("img")
        if not img:
            continue
        title_attr = img.get("title") or img.get("alt")
        if not title_attr or " by " not in title_attr:
            continue
        title, _, author = title_attr.rpartition(" by ")
        title, author = _ws(title), _ws(author)
        if not title or not author:
            continue
        key = (title.lower(), author.lower())
        if key in seen:
            continue
        seen.add(key)
        books.append(Book(title=title, author=author))
    return books
