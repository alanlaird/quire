# quire

Automated book acquisition: scrape curated book lists, skip what you already own, hand off the rest to Shelfmark for download into Calibre-Web-Automated.

## What it does

Quire polls one or more book-list sources (starting with the Goodreads Readers Choice Awards Science Fiction list), filters out titles you already have in Calibre-Web-Automated (CWA), and triggers Shelfmark to download the rest. Shelfmark drops files into CWA's ingest folder, where CWA converts and shelves them automatically.

It runs as a small CLI tool on a weekly cron, co-located on the host that runs Shelfmark and CWA. No manual steps after setup.

## Stack

- **Goodreads** (and other list sources, parameterized) — public HTML, scraped
- **Shelfmark** — search + download broker; tries AA (direct download) first, falls back to Prowlarr/MAM
- **hemlock** — KVM VM running qBittorrent + mlm via WireGuard VPN; seeds MAM downloads to `/pool/books/seed`, copies to `/pool/books/ingest`
- **fir** — NAS exporting `/pool/books/{seed,ingest,library}` over NFS to alienlord and hemlock
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
[Shelfmark: try AA (direct_download) first]
         |-- found --> download into /pool/books/ingest (NFS on fir)
         |-- not found --> Prowlarr/MAM search -> torrent -> seed on hemlock
                                                            |
                                                     /pool/books/ingest
[CWA: watches /pool/books/ingest, auto-ingest -> convert -> /pool/books/library]
         |
[Kobo sync / OPDS feeds]
```

State (queued titles, retry counts) lives in a small local file so reruns are idempotent.

## Components

- `src/quire/` — Python package
- `config.template.toml` — example config; copy to `config.toml` (gitignored) and populate
- `PLAN.md` — phased build plan
- `CLAUDE.md` — project context for Claude Code

## Usage

Set up a venv and install once:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
cp config.template.toml config.toml   # then edit
```

Inspect what's configured:

```sh
quire list-sources
```

Scrape a source and show the books it extracts. Default year is the current year from November on, the previous year otherwise (matches when the Goodreads Choice Awards page actually has data):

```sh
quire fetch goodreads-choice-awards-sf
```

Run it against a specific year — useful for smoke-testing extractors or backfilling:

```sh
quire fetch --year 2024 goodreads-choice-awards-sf
quire fetch --year 2025 goodreads-choice-awards-sf
```

Show which books from a source are already in CWA (combines scrape + OPDS dedup, no downloads):

```sh
quire check goodreads-choice-awards-sf
quire check --year 2024 goodreads-choice-awards-sf
```

Plan or execute the full pipeline (fetch + dedup + Shelfmark search + download):

```sh
quire run --dry-run                  # show what would happen, no downloads, no state writes
quire run                            # do it
quire run --year 2024                # one-off backfill of a prior year
```

Inspect the local state file (recorded queued / missed / gave-up entries):

```sh
quire state
```

Probe Shelfmark for a single title (handy for debugging matches):

```sh
quire shelfmark-search "Shroud" "Adrian Tchaikovsky"
```

## Status

Pipeline working end to end. Deployed on alienlord via the `quire` task in the alienlord ansible repo; runs weekly via cron (Sunday 04:17), emails a summary to `alan.laird@gmail.com`.

Calibre library lives at `/pool/books/library` on fir (NFS-mounted on alienlord as `/mnt/fir/books/library`). MAM torrents seed on hemlock (`/pool/books/seed`) then get imported via mlm into `/pool/books/ingest`.
