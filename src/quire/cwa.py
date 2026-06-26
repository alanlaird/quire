from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

from quire.config import CWAAuth
from quire.sources import Book

OPDS_NS = "{http://www.w3.org/2005/Atom}"


def is_owned(cwa: CWAAuth, book: Book) -> bool:
    url = f"{cwa.base_url.rstrip('/')}/opds/search/{quote(book.title, safe='')}"
    for attempt in range(4):
        try:
            resp = requests.get(url, auth=(cwa.username, cwa.password), timeout=60)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            return root.find(f"{OPDS_NS}entry") is not None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt == 3:
                return False  # CWA unreachable — assume not owned, let Shelfmark dedup
            time.sleep(10 * 2 ** attempt)  # 10s, 20s, 40s
