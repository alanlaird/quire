"""Hardcover GraphQL client — list read/write helpers for quire."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

HARDCOVER_API = "https://api.hardcover.app/v1/graphql"
RATE_SLEEP = 1.5


def gql(api_key: str, query: str, variables: dict | None = None, _attempt: int = 0) -> dict:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        HARDCOVER_API,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 429 and _attempt < 5:
            delay = 10 * (2 ** _attempt)
            time.sleep(delay)
            return gql(api_key, query, variables, _attempt + 1)
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}")
    except urllib.error.URLError as e:
        if _attempt < 5:
            delay = 10 * (2 ** _attempt)
            time.sleep(delay)
            return gql(api_key, query, variables, _attempt + 1)
        raise RuntimeError(f"network error: {e.reason}")
    if "errors" in data:
        msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
        raise RuntimeError(f"GraphQL: {msgs}")
    time.sleep(RATE_SLEEP)
    return data["data"]


def get_list_books(api_key: str, list_id: int) -> list[dict]:
    """Return [{book_id, title, author}, ...] for all books in a Hardcover list."""
    results = []
    offset = 0
    while True:
        d = gql(
            api_key,
            "query($lid: Int!, $lim: Int!, $off: Int!) {"
            "  list_books(where: {list_id: {_eq: $lid}}, limit: $lim, offset: $off) {"
            "    book_id"
            "    book { title contributions(limit: 1) { author { name } } }"
            "  }"
            "}",
            {"lid": list_id, "lim": 500, "off": offset},
        )
        batch = d["list_books"]
        for entry in batch:
            book = entry["book"]
            contribs = book.get("contributions") or []
            author = contribs[0]["author"]["name"] if contribs else ""
            results.append({
                "book_id": entry["book_id"],
                "title": book.get("title") or "",
                "author": author,
            })
        if len(batch) < 500:
            break
        offset += len(batch)
    return results


def remove_from_list(api_key: str, list_id: int, book_id: int) -> None:
    """Remove a book from a Hardcover list (no-op if not present)."""
    d = gql(
        api_key,
        "query($lid: Int!, $bid: Int!) {"
        "  list_books(where: {list_id: {_eq: $lid}, book_id: {_eq: $bid}}) { id }"
        "}",
        {"lid": list_id, "bid": book_id},
    )
    entries = d["list_books"]
    if not entries:
        return
    gql(
        api_key,
        "mutation($id: Int!) { delete_list_book(id: $id) { id } }",
        {"id": entries[0]["id"]},
    )


def add_to_list(api_key: str, list_id: int, book_id: int) -> None:
    """Add a book to a Hardcover list."""
    gql(
        api_key,
        "mutation($obj: ListBookInput!) { insert_list_book(object: $obj) { id } }",
        {"obj": {"list_id": list_id, "book_id": book_id}},
    )


def search_book(api_key: str, title: str, author: str) -> int | None:
    """Search Hardcover by title+author, return book_id or None."""
    d = gql(
        api_key,
        'query($q: String!) { search(query: $q, query_type: "book", per_page: 3) { results } }',
        {"q": f"{title} {author}".strip()},
    )
    results = (d.get("search") or {}).get("results")
    if not results:
        return None
    if isinstance(results, list):
        results = results[0] if results else {}
    hits = results.get("hits", []) if isinstance(results, dict) else []
    if not hits:
        return None
    raw_id = hits[0].get("document", {}).get("id")
    if not raw_id:
        return None
    return int(raw_id) if not isinstance(raw_id, int) else raw_id
