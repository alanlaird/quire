from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CWAAuth:
    base_url: str
    username: str
    password: str
    calibre_db: str = "/var/calibre-library/metadata.db"


@dataclass(frozen=True)
class ShelfmarkAuth:
    base_url: str


@dataclass(frozen=True)
class HardcoverAuth:
    api_key: str
    year_list_id: int  # list id for the current acquisition year (e.g. 450654 for "2026")


@dataclass(frozen=True)
class Source:
    name: str
    kind: str
    url_template: str | None = None
    list_id: int | None = None        # for hardcover_list sources: read FROM this list
    populate_list_id: int | None = None  # for scrape sources: write TO this list


@dataclass(frozen=True)
class EmailConfig:
    to: str
    from_addr: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    # Default False keeps the existing "always send" behavior — useful as a
    # weekly liveness ping. Flip to true to skip the email when nothing was
    # queued / missed / gave up this run.
    suppress_if_no_change: bool = False


@dataclass(frozen=True)
class MetricsConfig:
    path: Path


@dataclass(frozen=True)
class Config:
    shelfmark: ShelfmarkAuth
    cwa: CWAAuth
    state_path: Path
    email: EmailConfig
    sources: list[Source]
    hardcover: HardcoverAuth | None = None
    metrics: MetricsConfig | None = None


def load(path: Path) -> Config:
    with path.open("rb") as f:
        raw = tomllib.load(f)

    email_raw = dict(raw["email"])
    email_raw["from_addr"] = email_raw.pop("from")

    hardcover = None
    if "hardcover" in raw:
        hardcover = HardcoverAuth(**raw["hardcover"])

    metrics = None
    if "metrics" in raw:
        metrics = MetricsConfig(path=Path(raw["metrics"]["path"]).expanduser())

    return Config(
        shelfmark=ShelfmarkAuth(**raw["shelfmark"]),
        cwa=CWAAuth(**raw["cwa"]),
        state_path=Path(raw["state"]["path"]).expanduser(),
        email=EmailConfig(**email_raw),
        sources=[Source(**s) for s in raw["sources"]],
        hardcover=hardcover,
        metrics=metrics,
    )


def default_path() -> Path:
    return Path.cwd() / "config.toml"
