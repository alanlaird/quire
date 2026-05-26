from __future__ import annotations

from pathlib import Path

import click

from quire import config as cfg
from quire import cwa as cwa_client
from quire import shelfmark as sm
from quire import sources as src
from quire import state as st


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to config.toml (default: ./config.toml).",
)
@click.pass_context
def cli(ctx: click.Context, config_path: Path | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg.load(config_path or cfg.default_path())


@cli.command()
@click.option("--dry-run", is_flag=True, help="Search Shelfmark but don't trigger downloads or write state.")
@click.pass_context
def run(ctx: click.Context, dry_run: bool) -> None:
    config: cfg.Config = ctx.obj["config"]
    queued = 0
    skipped_owned = 0
    skipped_state = 0
    missed_no_match = 0
    gave_up = 0
    with st.open(config.state_path) as conn:
        for source in config.sources:
            click.echo(f"[{source.name}]")
            books = src.fetch(source)
            for book in books:
                prior = st.get(conn, source.name, book)
                if st.is_terminal(prior):
                    skipped_state += 1
                    continue
                if cwa_client.is_owned(config.cwa, book):
                    skipped_owned += 1
                    continue
                releases = sm.search(config.shelfmark, book)
                best = sm.pick_best(releases)
                if best is None:
                    if dry_run:
                        click.echo(f"  miss (dry-run): {book.title} — {book.author}")
                    else:
                        status = st.mark_missed(conn, source.name, book)
                        if status == st.STATUS_GAVE_UP:
                            gave_up += 1
                            click.echo(f"  gave up: {book.title} — {book.author}")
                        else:
                            missed_no_match += 1
                            click.echo(f"  miss: {book.title} — {book.author}")
                    continue
                label = f"{best.get('format')} {best.get('size')} via {best.get('indexer')}"
                if dry_run:
                    click.echo(f"  would queue [{label}]: {book.title} — {book.author}")
                else:
                    sm.download(config.shelfmark, best)
                    st.mark_queued(conn, source.name, book)
                    click.echo(f"  queued     [{label}]: {book.title} — {book.author}")
                queued += 1
    suffix = " (dry-run)" if dry_run else ""
    parts = [
        f"{queued} queued",
        f"{skipped_owned} owned",
        f"{skipped_state} skipped",
        f"{missed_no_match} no-match",
    ]
    if gave_up:
        parts.append(f"{gave_up} gave up")
    click.echo(f"summary{suffix}: " + ", ".join(parts))


@cli.command("list-sources")
@click.pass_context
def list_sources(ctx: click.Context) -> None:
    config: cfg.Config = ctx.obj["config"]
    for s in config.sources:
        click.echo(f"{s.name}\t{s.kind}\t{s.url_template}")


@cli.command()
@click.argument("name")
@click.pass_context
def fetch(ctx: click.Context, name: str) -> None:
    config: cfg.Config = ctx.obj["config"]
    source = next((s for s in config.sources if s.name == name), None)
    if source is None:
        raise click.ClickException(f"no source named {name!r}")
    books = src.fetch(source)
    click.echo(f"{source.name}: {len(books)} books")
    for b in books:
        click.echo(f"  {b.title} — {b.author}")


@cli.command()
@click.argument("name")
@click.pass_context
def check(ctx: click.Context, name: str) -> None:
    config: cfg.Config = ctx.obj["config"]
    source = next((s for s in config.sources if s.name == name), None)
    if source is None:
        raise click.ClickException(f"no source named {name!r}")
    books = src.fetch(source)
    owned: list[src.Book] = []
    missing: list[src.Book] = []
    for b in books:
        (owned if cwa_client.is_owned(config.cwa, b) else missing).append(b)
    click.echo(f"{source.name}: {len(books)} books, {len(owned)} owned, {len(missing)} missing")
    if missing:
        click.echo("missing:")
        for b in missing:
            click.echo(f"  {b.title} — {b.author}")


@cli.command()
@click.pass_context
def state(ctx: click.Context) -> None:
    config: cfg.Config = ctx.obj["config"]
    with st.open(config.state_path) as conn:
        rows = st.all_rows(conn)
    if not rows:
        click.echo("(empty)")
        return
    for r in rows:
        click.echo(f"  {r.status:<8} retries={r.retry_count} {r.last_attempted} [{r.source}] {r.title} — {r.author}")


@cli.command("shelfmark-search")
@click.argument("title")
@click.argument("author")
@click.pass_context
def shelfmark_search(ctx: click.Context, title: str, author: str) -> None:
    config: cfg.Config = ctx.obj["config"]
    releases = sm.search(config.shelfmark, src.Book(title=title, author=author))
    click.echo(f"{len(releases)} releases")
    for r in releases:
        click.echo(f"  {r.get('format'):<6} {r.get('size'):<8} {r.get('indexer'):<20} {r.get('title')}")
    best = sm.pick_best(releases)
    if best is not None:
        click.echo(f"best: {best.get('format')} {best.get('size')} ({best.get('source_id')})")
