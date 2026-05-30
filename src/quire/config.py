from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CWAAuth:
    base_url: str
    username: str
    password: str


@dataclass(frozen=True)
class ShelfmarkAuth:
    base_url: str


@dataclass(frozen=True)
class Source:
    name: str
    kind: str
    url_template: str


@dataclass(frozen=True)
class EmailConfig:
    to: str
    from_addr: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str


@dataclass(frozen=True)
class Config:
    shelfmark: ShelfmarkAuth
    cwa: CWAAuth
    state_path: Path
    email: EmailConfig
    sources: list[Source]


def load(path: Path) -> Config:
    with path.open("rb") as f:
        raw = tomllib.load(f)

    email_raw = dict(raw["email"])
    email_raw["from_addr"] = email_raw.pop("from")

    return Config(
        shelfmark=ShelfmarkAuth(**raw["shelfmark"]),
        cwa=CWAAuth(**raw["cwa"]),
        state_path=Path(raw["state"]["path"]).expanduser(),
        email=EmailConfig(**email_raw),
        sources=[Source(**s) for s in raw["sources"]],
    )


def default_path() -> Path:
    return Path.cwd() / "config.toml"
