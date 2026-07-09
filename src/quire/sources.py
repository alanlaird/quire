from __future__ import annotations

import csv
import io
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
    if source.kind == "hardcover_series":
        import quire.hardcover as hc
        if config.hardcover is None:
            raise ValueError("hardcover_series source requires [hardcover] config section")
        if source.list_id is None:
            raise ValueError(f"source {source.name!r} is missing list_id")
        seed = hc.get_list_books(config.hardcover.api_key, source.list_id)
        seed_ids = {e["book_id"] for e in seed}
        seen: set[int] = set()
        results: list[Book] = []
        for entry in seed:
            for series_id in hc.get_book_series_ids(config.hardcover.api_key, entry["book_id"]):
                for sibling in hc.get_series_books(config.hardcover.api_key, series_id):
                    book_id = sibling["book_id"]
                    if book_id in seed_ids or book_id in seen:
                        continue
                    seen.add(book_id)
                    results.append(Book(
                        title=sibling["title"],
                        author=sibling["author"],
                        hardcover_book_id=book_id,
                    ))
        return results
    if source.kind == "wikipedia_award_table":
        if source.url_template is None:
            raise ValueError(f"source {source.name!r} is missing url_template")
        html = _http_get(source.url_template)
        return _parse_award_wikitable(html, year=year)
    if source.kind == "award_sheet_csv":
        if source.url_template is None:
            raise ValueError(f"source {source.name!r} is missing url_template")
        text = _http_get(source.url_template, force_utf8=True)
        return _parse_award_sheet_csv(text, column=source.column)
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


def _http_get(url: str, force_utf8: bool = False) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    if force_utf8:
        # Google's CSV export answers `text/csv` with no charset, so requests
        # falls back to ISO-8859-1 and mangles the ✓ cells into mojibake.
        resp.encoding = "utf-8"
    return resp.text


def _parse_award_wikitable(html: str, year: int | None = None) -> list[Book]:
    """Parse a Wikipedia "Award for Best Novel" winners/nominees table.

    These pages share one layout: one or more `wikitable sortable` tables
    with columns Year [, Year awarded] / Author / Novel / Publisher / Ref
    (some pages split out a second "Retro" table for years awarded
    retroactively, with an extra "Year awarded" column — harmless here
    since it's still a `<th>`, not a `<td>`, so column indexing is
    unaffected). Year cells use `rowspan` and are only present on a
    group's first row (`scope="rowgroup"` for multi-nominee years,
    `scope="row"` for single-nominee years); Novel cells `rowspan`
    similarly when one book has multiple credited authors. Winners are
    marked with a trailing `*` in the author cell.
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", class_="wikitable")
    books: list[Book] = []
    seen: set[tuple[int, str, str]] = set()
    for table in tables:
        current_year: int | None = None
        current_title: str | None = None
        for tr in table.find_all("tr"):
            th = tr.find("th")
            if th is not None and th.get("scope") in ("row", "rowgroup"):
                year_text = _ws(th.get_text())
                current_year = int(year_text) if year_text.isdigit() else None
            tds = tr.find_all("td")
            if not tds or current_year is None:
                continue
            author = _ws(tds[0].get_text()).rstrip("*").strip()
            pen_name = re.search(r"\(as (.+?)\)\s*$", author)
            if pen_name:
                # credited under a pseudonym, e.g. "Ursula Vernon (as T. Kingfisher)" —
                # use the byline the book was actually published under
                author = pen_name.group(1).strip()
            if len(tds) >= 2:
                title = _ws(tds[1].get_text())
                current_title = re.sub(r"\s*\(also known as.*?\)\s*$", "", title, flags=re.IGNORECASE).strip()
            title = current_title
            if not title or not author:
                continue
            if year is not None and current_year != year:
                continue
            key = (current_year, title.lower(), author.lower())
            if key in seen:
                continue
            seen.add(key)
            books.append(Book(title=title, author=author))
    return books


def _parse_award_sheet_csv(text: str, column: str | None = None) -> list[Book]:
    """Parse the "SF book awards & best-of consensus" Google Sheet CSV export.

    One row per book, with a ✓/× cell per award / best-of-list column
    ("Hugo", "Locus SF & F Award", "SF Masterworks", ...). `column` filters
    to rows ticked ✓ for that column; omit it to return every row. It's a
    curated consensus list, not an exhaustive nominee roll — see books.md
    (alienlord) "award data sources surveyed" for the caveats.

    Multi-author rows use "A & B" (e.g. "Mark Clifton & Frank Riley") —
    only the first-credited author is kept, since that's enough for the
    Hardcover title+author search to resolve the book.
    """
    books: list[Book] = []
    seen: set[tuple[str, str]] = set()
    for row in csv.DictReader(io.StringIO(text)):
        if column is not None and _ws(row.get(column) or "") != "✓":
            continue
        title = _ws(row.get("Book Title") or "")
        author = _ws((row.get("Author") or "").split("&")[0])
        if not title or not author:
            continue
        key = (title.lower(), author.lower())
        if key in seen:
            continue
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
