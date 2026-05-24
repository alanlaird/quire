from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServiceAuth:
    base_url: str
    username: str
    password: str


@dataclass(frozen=True)
class Source:
    name: str
    kind: str
    url_template: str


@dataclass(frozen=True)
class Config:
    shelfmark: ServiceAuth
    cwa: ServiceAuth
    state_path: Path
    email_to: str
    sources: list[Source]


def load(path: Path) -> Config:
    with path.open("rb") as f:
        raw = tomllib.load(f)

    return Config(
        shelfmark=ServiceAuth(**raw["shelfmark"]),
        cwa=ServiceAuth(**raw["cwa"]),
        state_path=Path(raw["state"]["path"]).expanduser(),
        email_to=raw["email"]["to"],
        sources=[Source(**s) for s in raw["sources"]],
    )


def default_path() -> Path:
    return Path.cwd() / "config.toml"
