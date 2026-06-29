from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

from quire.config import ShelfmarkAuth
from quire.sources import Book

FORMAT_PRIORITY = ("epub", "mobi", "azw3")


def _search_aa(base_url: str, book: Book) -> list[dict[str, Any]]:
    params = urlencode({"query": f"{book.title} {book.author}", "source": "direct_download"})
    resp = requests.get(f"{base_url.rstrip('/')}/api/releases?{params}", timeout=60)
    resp.raise_for_status()
    return resp.json().get("releases", [])


def _search_prowlarr(base_url: str, book: Book) -> list[dict[str, Any]]:
    # MAM entries rarely include subtitles — strip after first comma/colon
    short_title = book.title.split(",")[0].split(":")[0].strip()
    params = urlencode({
        "provider": "manual",
        "book_id": "prowlarr-search",
        "title": short_title,
        "author": book.author,
        "source": "prowlarr",
    })
    resp = requests.get(f"{base_url.rstrip('/')}/api/releases?{params}", timeout=60)
    resp.raise_for_status()
    return resp.json().get("releases", [])


def search(shelfmark: ShelfmarkAuth, book: Book) -> list[dict[str, Any]]:
    releases = _search_aa(shelfmark.base_url, book)
    if not releases:
        releases = _search_prowlarr(shelfmark.base_url, book)
    return releases


def pick_best(releases: list[dict[str, Any]]) -> dict[str, Any] | None:
    for fmt in FORMAT_PRIORITY:
        for r in releases:
            if (r.get("format") or "").lower() == fmt:
                return r
    return None


class DownloadError(Exception):
    pass


def download(shelfmark: ShelfmarkAuth, release: dict[str, Any]) -> None:
    url = f"{shelfmark.base_url.rstrip('/')}/api/releases/download"
    resp = requests.post(url, json=release, timeout=60)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise DownloadError(str(e)) from e
