from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

from quire.config import ShelfmarkAuth
from quire.sources import Book

FORMAT_PRIORITY = ("epub", "mobi", "azw3")


def search(shelfmark: ShelfmarkAuth, book: Book) -> list[dict[str, Any]]:
    query = urlencode({"query": f"{book.title} {book.author}"})
    url = f"{shelfmark.base_url.rstrip('/')}/api/releases?source=direct_download&{query}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json().get("releases", [])


def pick_best(releases: list[dict[str, Any]]) -> dict[str, Any] | None:
    for fmt in FORMAT_PRIORITY:
        for r in releases:
            if (r.get("format") or "").lower() == fmt:
                return r
    return None


def download(shelfmark: ShelfmarkAuth, release: dict[str, Any]) -> None:
    url = f"{shelfmark.base_url.rstrip('/')}/api/releases/download"
    resp = requests.post(url, json=release, timeout=60)
    resp.raise_for_status()
