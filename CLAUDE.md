# quire — project context

Personal automation. Watches book-list sources (starting with Goodreads Choice Awards SF), dedupes against Calibre-Web-Automated, hands off downloads to Shelfmark.

## Shape

- Python CLI tool, weekly cron on a small Alpine homelab host
- Parameterized list-source config — adding a source is a config entry (+ maybe an extractor module), not a workflow rewrite
- Fully automatic; no human approval gate
- No n8n, no GitHub PAT, no remote config fetch — repo is code + templates, host carries `config.toml`

## Services

- **Shelfmark** — `https://shelfmark.radi8.org`, basic auth. In maintenance mode (stable). Download target already wired to CWA ingest.
- **CWA** — `https://cwa.radi8.org`, basic auth. Signup is open; anonymous browsing is intentionally off. Create a dedicated read-only `quire` user for the pipeline rather than reusing admin.

Credentials live in `config.toml` on the host (gitignored). A populated `config.template.toml` is checked into the repo.

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

## Open items (not in PLAN.md)

- Pick the Alpine host that will run the cron
- Create the read-only `quire` user in CWA
- Rotate the shared basic-auth password after the pipeline is wired (tracked in `~/dotclaude/tasks.md`)
- Decide email transport (deferred — picked at Phase 7)
