from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

import requests
from bs4 import BeautifulSoup

from quire.config import Source

USER_AGENT = "quire/0.1 (+https://github.com/alanlaird/quire)"


@dataclass(frozen=True)
class Book:
    title: str
    author: str


Extractor = Callable[[str], list[Book]]
_REGISTRY: dict[str, Extractor] = {}


def register(kind: str) -> Callable[[Extractor], Extractor]:
    def decorator(fn: Extractor) -> Extractor:
        _REGISTRY[kind] = fn
        return fn
    return decorator


def fetch(source: Source, year: int | None = None) -> list[Book]:
    if source.kind not in _REGISTRY:
        raise ValueError(f"unknown source kind: {source.kind}")
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
