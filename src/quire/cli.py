from __future__ import annotations

from pathlib import Path

import click

from quire import config as cfg


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
