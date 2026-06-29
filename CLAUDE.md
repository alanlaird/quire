# quire — project context

Personal automation. Watches book-list sources (starting with Goodreads Choice Awards SF), dedupes against Calibre-Web-Automated, hands off downloads to Shelfmark.

## Shape

- Python CLI tool, weekly cron on `alienlord` (same Debian host as CWA + Shelfmark)
- Parameterized list-source config — adding a source is a config entry (+ maybe an extractor module), not a workflow rewrite
- Fully automatic; no human approval gate
- No n8n, no GitHub PAT, no remote config fetch — repo is code + templates, host carries `config.toml`

## Services and auth

quire reaches both services over loopback on alienlord, bypassing Caddy entirely. The public stack (managed in `~/web/alienlord`) has a cookie gate at `library.radi8.org` that fronts `shelfmark.radi8.org`; loopback skips that.

- **Shelfmark** — `http://localhost:8084`. No auth required from loopback. Public access is cookie-gated by Caddy; quire avoids that surface by running on-box. In maintenance mode (stable). Download target: `/mnt/fir/books/ingest` (NFS from fir).
- **CWA** — `http://localhost:8083`. Basic auth at the app layer with a dedicated read-only `quire` user (`ROLE_DOWNLOAD | ROLE_VIEWER`, created via direct INSERT into `/var/config/app.db` on 2026-05-23). Public `cwa.radi8.org` is intentionally not behind the cookie gate, but the OPDS endpoint requires basic auth regardless of source IP. Calibre library at `/mnt/fir/books/library` (NFS from fir).

## Download pipeline

Shelfmark tries sources in order:
1. **AA (direct_download)** — `source=direct_download`, full title+author query; fast, no torrent
2. **Prowlarr/MAM** — falls back when AA returns nothing; `source=prowlarr` with stripped short title (no subtitle after first `,` or `:`); triggers qBittorrent on hemlock via WireGuard VPN; mlm copies finished downloads to `/pool/books/ingest`

The Prowlarr container runs on hemlock (172.16.16.70 / Tailscale 100.123.227.68:9696). Shelfmark reaches it via Tailscale; the WireGuard PostUp on hemlock adds a bypass route for `100.64.0.0/10` so Tailscale traffic isn't routed through ProtonVPN.

Credentials live in `config.toml` on alienlord (gitignored). A populated `config.template.toml` is checked into the repo. For local dev, SSH-tunnel both ports: `ssh -L 8083:localhost:8083 -L 8084:localhost:8084 alienlord.toad.love`.

## Design decisions worth remembering

- **Format priority**: epub > mobi > azw3
- **Match strictness**: trust CWA's OPDS search; no client-side title/author normalization. CWA's ingest-time dedup is the safety net.
- **Vote threshold**: dropped. Take all ~20 nominees per source; CWA dedup handles repeats.
- **No-match handling**: skip + retry on next poll. State tracks retry count so we back off after N attempts.
- **Cadence**: weekly year-round. Simpler than tracking which sources have active voting windows.

## Repo layout

- `src/quire/` — Python package
- `sources/` — list-source definitions
- `config.template.toml` — copy to `config.toml`, populate, gitignored
- `docs/` — API discovery notes, design notes
- `PLAN.md` — phased build plan
- `README.md` — user-facing
- `CLAUDE.md` — this file

## Owner

Personal project, alanlaird. Not affiliated with arcwerx.

## Deploy

quire is deployed to alienlord by the `quire` task in `~/web/alienlord/roles/common/tasks/quire.yml`. Vault keys it reads: `quire_cwa_password`, `cwa_mail_password`. Cron entry: `Sunday 04:17`, output appended to `/var/log/quire.log`.

## Open items (not in PLAN.md)

- (none)
