# quire — Build Plan

## Overview

Python CLI tool, weekly cron on a small Alpine host. Reads a parameterized list of book sources, dedupes against CWA OPDS, hands off to Shelfmark. State is a local file so reruns are safe.

## Prerequisites

- Shelfmark instance running, with download destination pointed at CWA ingest (already wired)
- Calibre-Web-Automated running with OPDS enabled
- Dedicated read-only `quire` user created in CWA (don't reuse admin creds)
- Python 3.11+ available on the target host
- An Alpine homelab host with cron and persistent storage for the state file

## Phase 1 — Project skeleton + config

- `pyproject.toml` + `src/quire/` package
- CLI entry point: `quire run`, `quire run --dry-run`, `quire list-sources`
- `config.template.toml` committed; `config.toml` gitignored
- Config carries: Shelfmark base URL + auth, CWA base URL + auth, state file path, sources list, email destination
- README points users at the template

## Phase 2 — API discovery (~1 hour)

Before any scrape/download code, capture API shapes from browser devtools:

1. Shelfmark search — open devtools Network tab, search a book, capture URL/method/params/headers
2. Shelfmark download — click download, capture the request
3. CWA OPDS — verify `GET https://cwa.radi8.org/opds/search/<title>` shape and auth
4. Document in `docs/api-discovery.md`

## Phase 3 — Source extractors

- Source config schema: `{name, url_template, extractor_kind, ...}`
- First implementation: Goodreads Choice Awards (`extractor_kind: "goodreads_choice_awards"`)
- URL template substitutes current year
- Returns `[{title, author}]` for all nominees on the page
- Designed so adding a new source is "add an entry + maybe a new extractor kind"

## Phase 4 — CWA OPDS dedup

- For each `{title, author}`, query CWA OPDS search
- Skip if any result is returned (trust CWA's match — no client-side normalization)
- Pass misses to Phase 5

## Phase 5 — Shelfmark search + download

- POST to Shelfmark search endpoint
- Filter results by format priority: epub > mobi > azw3
- If no acceptable result, mark as miss in state and move on (retry next run)
- Otherwise, POST to Shelfmark download endpoint
- Wait briefly between downloads to be polite

## Phase 6 — State + retry

- Local state file (sqlite or JSON, whichever fits the data shape)
- Tracks: title, author, source, status (queued / downloaded / missed), retry count, last-attempted timestamp
- On each run, retry misses; back off after N attempts so a permanently-unavailable title doesn't churn forever

## Phase 7 — Email summary + cron

- Summary email to `alan@laird.net` after each run: queued, skipped (already owned), missed (no Shelfmark result)
- Email transport TBD — pick simplest at implementation time
- Deploy via crontab on the chosen Alpine host (weekly)

## Build order

1. Phase 1 — skeleton + config (unblocks everything else)
2. Phase 2 — API discovery (unblocks Phase 5)
3. Phase 3 — Goodreads extractor with a fixed sample HTML, no network
4. Phase 4 — CWA OPDS dedup against a real CWA instance
5. Phase 5 — Shelfmark search/download, end-to-end test with one known-missing title
6. Phase 6 — state file + retry logic
7. Phase 7 — email + cron deployment

## Notes

- CWA v4.0.6+ has smart duplicate handling on ingest — safety net if the OPDS check ever lets a duplicate through
- Shelfmark is in maintenance mode (stable, no new features expected)
- No n8n, no GitHub PAT, no remote config fetch — everything lives in this repo + the host's config file
