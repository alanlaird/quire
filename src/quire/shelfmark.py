from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

from quire.config import ShelfmarkAuth
from quire.sources import Book

FORMAT_PRIORITY = ("epub", "mobi", "azw3")


def _search_aa(base_url: str, book: Book) -> list[dict[str, Any]]:
    params = urlencode({"query": f"{book.title} {book.author}", "source": "direct_download"})
    # Shelfmark's Cloudflare bypasser against Anna's Archive can burn ~90s across
    # its retry ladder before giving up; give it room to actually finish instead
    # of us aborting first and never finding out whether it would have worked.
    resp = requests.get(f"{base_url.rstrip('/')}/api/releases?{params}", timeout=100)
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


def _search_newznab(base_url: str, book: Book) -> list[dict[str, Any]]:
    params = urlencode({
        "provider": "manual",
        "book_id": "newznab-search",
        "title": book.title,
        "author": book.author,
        "source": "newznab",
    })
    resp = requests.get(f"{base_url.rstrip('/')}/api/releases?{params}", timeout=60)
    resp.raise_for_status()
    return resp.json().get("releases", [])


def search(shelfmark: ShelfmarkAuth, book: Book) -> list[dict[str, Any]]:
    # Usenet first: fast, no Cloudflare bypass drama, no MAM-account-abuse
    # risk — worth checking even though its book catalog is smaller than
    # AA's or MAM's, since a hit there costs nothing on either of the other
    # two. Falls through to AA, then MAM/torrent, on a miss or any error.
    try:
        releases = _search_newznab(shelfmark.base_url, book)
    except requests.exceptions.RequestException:
        releases = []
    if not releases:
        try:
            releases = _search_aa(shelfmark.base_url, book)
        except requests.exceptions.RequestException:
            # AA down/blocked/timed out — fall through to the Prowlarr/torrent
            # source below instead of failing the whole search.
            releases = []
    if not releases:
        releases = _search_prowlarr(shelfmark.base_url, book)
    return releases


def _release_format(release: dict[str, Any]) -> str:
    """The release's format, falling back to sniffing it out of the title.

    Newznab (and possibly Prowlarr/torrent) results routinely come back with
    `format: null` — NZB/torrent search results don't carry structured
    per-file metadata the way AA's listings do, but the format is almost
    always spelled out in the title text (e.g. "...Retail.EPUB.eBook-...").
    """
    fmt = (release.get("format") or "").lower()
    if fmt:
        return fmt
    title = (release.get("title") or "").lower()
    for candidate in FORMAT_PRIORITY:
        if candidate in title:
            return candidate
    return ""


def pick_best(releases: list[dict[str, Any]]) -> dict[str, Any] | None:
    for fmt in FORMAT_PRIORITY:
        for r in releases:
            if _release_format(r) == fmt:
                return r
    return None


class DownloadError(Exception):
    pass


def download(shelfmark: ShelfmarkAuth, release: dict[str, Any]) -> None:
    url = f"{shelfmark.base_url.rstrip('/')}/api/releases/download"
    resp = requests.post(url, json=release, timeout=60)
    if resp.status_code == 500:
        body = resp.json() if resp.content else {}
        if "already in the download queue" in body.get("error", ""):
            return
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise DownloadError(str(e)) from e
