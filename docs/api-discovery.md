# API discovery

Endpoint shapes for the services quire calls. Captured against the live alienlord stack on 2026-05-26.

---

## Shelfmark — search

Looks up downloadable releases for a free-text query. Backed by Shelfmark's "direct download" provider (Anna's Archive).

- URL: `GET {base}/api/releases?source=direct_download&query=<URL-encoded "title author">`
- Auth: none from loopback (Caddy cookie gate bypassed). Public access would also need `X-Auth` or the `library_session` cookie.
- Response: JSON object with keys `book`, `column_config`, `releases`, `search_info`, `sources_searched`.

Sample release entry (trimmed):

```json
{
  "format": "epub",
  "title": "Shroud",
  "size": "1.8MB",
  "indexer": "Direct Download",
  "source": "direct_download",
  "source_id": "897622181c7058f34ed83a47f8842d9e",
  "info_url": "https://annas-archive.pk/md5/...",
  "language": "en",
  "extra": { "author": "Tchaikovsky, Adrian", "language": "en", "year": "2024", ... }
}
```

quire filters `releases[].format` for `epub > mobi > azw3` and picks the first hit in that priority order. Other formats (e.g. `fb2`) are skipped.

---

## Shelfmark — download

Triggers a download to the configured destination (which on alienlord is wired to CWA ingest).

- URL: `POST {base}/api/releases/download`
- Auth: same as search (none from loopback).
- Body: the full release object returned by search, JSON-encoded. Optional `on_behalf_of_user_id: <int>` if running on behalf of another user; quire doesn't set it.
- Response: success returns 2xx with no meaningful body; failures return error JSON.

---

## CWA — OPDS search

- URL: `GET {base}/opds/search/<URL-encoded title>`
- Auth: HTTP basic against the dedicated `quire` user (role `ROLE_DOWNLOAD | ROLE_VIEWER`).
- Response: Atom XML feed.
- Owned check: any `<entry>` element under the root `<feed>` = title is in the library. Empty feed (no entries) = not owned.

The OpenSearch description at `GET {base}/opds/osd` confirms the path template: `/opds/search/{searchTerms}`.

---

## Notes

- Shelfmark uses socket.io for live search-status / download-progress updates. quire doesn't need that — it polls the REST endpoints synchronously and doesn't care about progress streaming.
- The Shelfmark frontend has a separate "metadata search" mode (`GET /api/metadata/search`) that queries metadata providers (Google Books, etc.) for cover/info enrichment. quire skips this and goes straight to `/api/releases?source=direct_download`.
- Shelfmark source: https://github.com/calibrain/shelfmark (MIT, Python).
