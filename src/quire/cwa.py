from __future__ import annotations

import sys
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

from quire.config import CWAAuth
from quire.sources import Book

OPDS_NS = "{http://www.w3.org/2005/Atom}"


def _cwa_get(cwa: CWAAuth, url: str) -> requests.Response:
    """GET url with retry + wait-loop when CWA is unresponsive."""
    _RETRY_DELAYS = [5, 10, 20]
    for delay in _RETRY_DELAYS:
        try:
            return requests.get(url, auth=(cwa.username, cwa.password), timeout=60)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(delay)
    wait = 60
    while True:
        print(f"[cwa] unresponsive — waiting {wait}s before retry", file=sys.stderr, flush=True)
        time.sleep(wait)
        wait = min(wait * 2, 300)
        try:
            return requests.get(url, auth=(cwa.username, cwa.password), timeout=60)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue


def load_library(cwa: CWAAuth) -> set[str]:
    """Read all titles from Calibre metadata.db directly. Returns lowercased title set."""
    import sqlite3
    db = cwa.calibre_db
    conn = sqlite3.connect(db, timeout=30)
    try:
        rows = conn.execute("SELECT title FROM books").fetchall()
        return {r[0].lower() for r in rows}
    finally:
        conn.close()


def is_owned(cwa: CWAAuth, book: Book, library: set[str] | None = None) -> bool:
    if library is not None:
        return book.title.lower() in library
    url = f"{cwa.base_url.rstrip('/')}/opds/search/{quote(book.title, safe='')}"
    resp = _cwa_get(cwa, url)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    return root.find(f"{OPDS_NS}entry") is not None
