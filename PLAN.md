# quire — Build Plan

## Overview

Python CLI tool, weekly cron on `alienlord` (Debian, same host as CWA + Shelfmark). Reads a parameterized list of book sources, dedupes against CWA OPDS, hands off to Shelfmark. State is a local file so reruns are safe.

Co-locating on alienlord lets quire reach both services over loopback (`http://localhost:8083` for CWA, `http://localhost:8084` for Shelfmark), bypassing Caddy's cookie gate entirely. CWA's app-level OPDS basic auth still applies; Shelfmark is reachable without any auth from loopback.

## Prerequisites

- Shelfmark instance running on alienlord at `localhost:8084`, with download destination pointed at CWA ingest (already wired)
- Calibre-Web-Automated running on alienlord at `localhost:8083` with OPDS enabled
- Dedicated read-only `quire` user created in CWA (already exists, role `ROLE_DOWNLOAD | ROLE_VIEWER`)
- Python 3.11+ available on alienlord
- For local dev: `ssh -L 8083:localhost:8083 -L 8084:localhost:8084 alienlord.toad.love`

## Phase 1 — Project skeleton + config

- `pyproject.toml` + `src/quire/` package
- CLI entry point: `quire run`, `quire run --dry-run`, `quire list-sources`
- `config.template.toml` committed; `config.toml` gitignored
- Config carries: Shelfmark base URL + auth, CWA base URL + auth, state file path, sources list, email destination
- README points users at the template

## Phase 2 — API discovery (~1 hour)

Before any Shelfmark integration, capture API shapes. CWA OPDS shape is confirmed (`GET /opds/search/{searchTerms}`, basic auth, Atom feed). Remaining work: Shelfmark search + download endpoints, captured via browser devtools and documented in `docs/api-discovery.md`.

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

Done.

- Summary email implemented in `src/quire/notify.py` (stdlib smtplib + STARTTLS). Sent after each live `quire run` unless `--no-email` is passed; dry-run never sends.
- Transport reuses the existing alienlord Gmail SMTP credential (`smtp_login = ottomatethis@gmail.com`, password from vault key `cwa_mail_password`). Email goes to the global `email` var (`alan.laird@gmail.com`).
- Deploy is an ansible role at `~/web/alienlord/roles/common/tasks/quire.yml`, wired into `playbook.yml` after the firewall step. The role clones to `/opt/quire`, builds a venv, `pip install -e .`'s the package, templates `/opt/quire/config.toml` (0600) from `roles/common/templates/quire-config.toml.j2`, and installs a Sunday 04:17 weekly cron that appends to `/var/log/quire.log`.

### Deploy procedure

1. Add `quire_cwa_password: "<value from quire/config.toml>"` to `~/web/alienlord/group_vars/all/vault.yml` (use `ansible-vault edit`).
2. `cd ~/web/alienlord && ansible-playbook playbook.yml` (or limit to the quire role with `--start-at-task "Install quire (book acquisition pipeline)"`).
3. Verify: `ssh alienlord.toad.love sudo /opt/quire/.venv/bin/quire --config /opt/quire/config.toml run --dry-run`.
4. First real run will happen at the next Sunday 04:17, or trigger immediately by dropping `--dry-run`.

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
