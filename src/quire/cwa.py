from __future__ import annotations

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
    # Retries exhausted — enter wait loop until CWA recovers
    import sys
    wait = 60
    while True:
        print(f"[cwa] unresponsive — waiting {wait}s before retry", file=sys.stderr, flush=True)
        time.sleep(wait)
        wait = min(wait * 2, 300)
        try:
            return requests.get(url, auth=(cwa.username, cwa.password), timeout=60)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue


def is_owned(cwa: CWAAuth, book: Book) -> bool:
    url = f"{cwa.base_url.rstrip('/')}/opds/search/{quote(book.title, safe='')}"
    resp = _cwa_get(cwa, url)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    return root.find(f"{OPDS_NS}entry") is not None
