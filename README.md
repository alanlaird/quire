# quire

Automated book acquisition: scrape curated book lists, skip what you already own, hand off the rest to Shelfmark for download into Calibre-Web-Automated.

## What it does

Quire polls one or more book-list sources (starting with the Goodreads Readers Choice Awards Science Fiction list), filters out titles you already have in Calibre-Web-Automated (CWA), and triggers Shelfmark to download the rest. Shelfmark drops files into CWA's ingest folder, where CWA converts and shelves them automatically.

It runs as a small CLI tool on a weekly cron — no manual steps after setup.

## Stack

- **Goodreads** (and other list sources, parameterized) — public HTML, scraped
- **Shelfmark** — search + download broker
- **Calibre-Web-Automated** — library ingest, dedup, format conversion, device sync

## Architecture

```
[list source: Goodreads Choice Awards SF, ...]
         |  (HTTP scrape, weekly)
[quire: extract -> [{title, author}]]
         |
[quire: query CWA OPDS, filter already-owned]
         |
[quire: Shelfmark search -> pick best (epub > mobi > azw3)]
         |
[Shelfmark: download into CWA ingest dir]
         |
[CWA: auto-ingest -> convert -> library]
         |
[Kobo sync / OPDS feeds]
```

State (queued titles, retry counts) lives in a small local file so reruns are idempotent.

## Components

- `src/quire/` — Python package
- `config.template.toml` — example config; copy to `config.toml` (gitignored) and populate
- `sources/` — list-source definitions (URL templates, extractors, schedule hints)
- `PLAN.md` — phased build plan
- `CLAUDE.md` — project context for Claude Code

## Status

Early development. Design complete, implementation in progress.
