# quire

Automated book acquisition pipeline: Goodreads award lists → Shelfmark → Calibre-Web-Automated.

## What it does

Quire watches the Goodreads Readers Choice Awards Science Fiction list, checks your Calibre library for titles you don't already own, and triggers Shelfmark to download new titles automatically. Books land in Calibre-Web-Automated's ingest folder and are processed into your library without any manual steps.

## Stack

- **Goodreads** — source list (public HTML, scraped annually)
- **Shelfmark** — search and download broker
- **Calibre-Web-Automated (CWA)** — library ingest, dedup, format conversion, device sync

## Architecture

```
[Goodreads Choice Awards SF page]
         ↓  (HTTP scrape, annual schedule)
[n8n: Extract book list → [{title, author}]]
         ↓
[n8n: Diff → filter already-known titles via CWA OPDS]
         ↓
[Shelfmark: search → pick best result → trigger download]
         ↓  (file lands in CWA ingest dir)
[CWA: auto-ingest → convert → library]
         ↓
[Kobo sync / OPDS feeds]
```

## Components

- `workflows/` — n8n workflow JSON exports
- `docs/` — design notes and API discovery findings
- `PLAN.md` — phased build plan
- `CLAUDE.md` — project context for Claude Code

## Status

Early development. Pipeline design complete, implementation in progress.
