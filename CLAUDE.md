# quire

Automated book acquisition pipeline: Goodreads Choice Awards SF list → Shelfmark → Calibre-Web-Automated.

## What this project does

Watches the annual Goodreads Readers Choice SF list, checks CWA OPDS to filter already-owned titles, then triggers Shelfmark to download new ones. Books land in CWA ingest and are auto-processed into the library.

## Stack

- n8n (orchestration, at n8n.radi8.org, on Kubernetes)
- Shelfmark (book search and download)
- Calibre-Web-Automated / CWA (library, OPDS, device sync)
- Goodreads public HTML (source list, no auth)

## Key unknowns — resolve first

- Shelfmark search endpoint: capture via browser devtools
- Shelfmark download endpoint: capture via browser devtools
- CWA OPDS search: GET http://<cwa-host>/opds/search/<title>

Document in docs/api-discovery.md before building.

## Repo structure

- workflows/ — n8n workflow JSON exports
- docs/ — API discovery notes, design decisions
- PLAN.md — phased build plan
- CLAUDE.md — this file

## Owner

Personal project, alanlaird. Not affiliated with arcwerx.
