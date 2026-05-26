from __future__ import annotations

from pathlib import Path

import click

from quire import config as cfg
from quire import cwa as cwa_client
from quire import sources as src


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
@click.option("--dry-run", is_flag=True, help="Plan only; no scraping, no downloads.")
@click.pass_context
def run(ctx: click.Context, dry_run: bool) -> None:
    config: cfg.Config = ctx.obj["config"]
    mode = "dry-run" if dry_run else "live"
    click.echo(f"quire run ({mode})")
    click.echo(f"  sources: {len(config.sources)}")
    for s in config.sources:
        click.echo(f"    - {s.name} ({s.kind})")
    click.echo("  pipeline not yet implemented (Phases 3-6)")


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
