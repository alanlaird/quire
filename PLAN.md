# quire — Build Plan

## Overview

Three-service pipeline automating SF book acquisition from Goodreads Choice Awards into a Calibre library.

## Prerequisites

- Shelfmark instance running with download destination pointed at CWA ingest folder
- Calibre-Web-Automated (CWA) running with OPDS enabled
- n8n instance (existing at n8n.radi8.org)
- GitHub Personal Access Token with repo scope

## Phase 1 — API Discovery (~1 hour)

Before building anything in n8n, capture Shelfmark API shape via browser devtools:

1. Open devtools Network tab on your Shelfmark instance
2. Search for a book — capture request URL, method, params, headers
3. Click download — capture the download request
4. Document in docs/api-discovery.md

Also verify CWA OPDS:
```
GET http://<cwa-host>/opds/search/<title>
```

## Phase 2 — Goodreads Scraper

Standalone n8n workflow:
- Manual trigger (later: annual schedule in December)
- HTTP GET Goodreads Choice Awards SF page for current year
- HTML Extract node — pull title + author from nominee cards
- Output: JSON array of {title, author} (~20 books)

## Phase 3 — CWA Duplicate Check

- For each title, query CWA OPDS search endpoint
- Found in library → skip
- Not found → pass to Phase 4
- n8n DataTable as fallback cache for already-queued titles

## Phase 4 — Shelfmark Download Trigger

- HTTP POST to Shelfmark search endpoint
- Parse response, select best match
- HTTP POST to Shelfmark download endpoint
- Write to n8n DataTable (mark queued)
- Wait 30-60s between downloads

## Phase 5 — Schedule and Notify

- Annual schedule trigger (December)
- Summary notification of queued titles

## Build Order

1. API discovery — unblocks everything
2. Goodreads scraper — validate list parsing
3. CWA OPDS check — validate duplicate detection
4. Shelfmark trigger — wire together
5. End-to-end test with one known title
6. Schedule and notifications

## Notes

- CWA v4.0.6+ has smart duplicate handling on ingest as safety net
- Shelfmark is in maintenance mode — stable, no new features expected
- Use Claude Code locally for future development work
