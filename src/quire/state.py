from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from quire.sources import Book

MAX_MISS_RETRIES = 4
STATUS_QUEUED = "queued"
STATUS_OWNED = "owned"
STATUS_MISSED = "missed"
STATUS_GAVE_UP = "gave_up"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    source TEXT NOT NULL,
    title  TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_attempted TEXT NOT NULL,
    PRIMARY KEY (source, title, author)
);
"""


@dataclass(frozen=True)
class Row:
    source: str
    title: str
    author: str
    status: str
    retry_count: int
    last_attempted: str


@contextmanager
def open(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get(conn: sqlite3.Connection, source: str, book: Book) -> Row | None:
    r = conn.execute(
        "SELECT source, title, author, status, retry_count, last_attempted "
        "FROM books WHERE source=? AND title=? AND author=?",
        (source, book.title, book.author),
    ).fetchone()
    return Row(**dict(r)) if r else None


def is_terminal(row: Row | None) -> bool:
    if row is None:
        return False
    return row.status in (STATUS_QUEUED, STATUS_OWNED, STATUS_GAVE_UP)


def mark_queued(conn: sqlite3.Connection, source: str, book: Book) -> None:
    conn.execute(
        "INSERT INTO books (source, title, author, status, retry_count, last_attempted) "
        "VALUES (?, ?, ?, ?, 0, ?) "
        "ON CONFLICT(source, title, author) DO UPDATE SET "
        "  status=excluded.status, retry_count=0, last_attempted=excluded.last_attempted",
        (source, book.title, book.author, STATUS_QUEUED, _now()),
    )


def mark_owned(conn: sqlite3.Connection, source: str, book: Book) -> None:
    conn.execute(
        "INSERT INTO books (source, title, author, status, retry_count, last_attempted) "
        "VALUES (?, ?, ?, ?, 0, ?) "
        "ON CONFLICT(source, title, author) DO UPDATE SET "
        "  status=excluded.status, retry_count=0, last_attempted=excluded.last_attempted",
        (source, book.title, book.author, STATUS_OWNED, _now()),
    )


def mark_missed(conn: sqlite3.Connection, source: str, book: Book) -> str:
    prior = get(conn, source, book)
    new_count = (prior.retry_count + 1) if prior else 1
    status = STATUS_GAVE_UP if new_count >= MAX_MISS_RETRIES else STATUS_MISSED
    conn.execute(
        "INSERT INTO books (source, title, author, status, retry_count, last_attempted) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(source, title, author) DO UPDATE SET "
        "  status=excluded.status, retry_count=excluded.retry_count, "
        "  last_attempted=excluded.last_attempted",
        (source, book.title, book.author, status, new_count, _now()),
    )
    return status


_RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    TEXT NOT NULL,
    queued      INTEGER NOT NULL DEFAULT 0,
    owned       INTEGER NOT NULL DEFAULT 0,
    skipped     INTEGER NOT NULL DEFAULT 0,
    no_match    INTEGER NOT NULL DEFAULT 0,
    gave_up     INTEGER NOT NULL DEFAULT 0
);
"""


@contextmanager
def open_metrics(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_RUNS_SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def record_run(
    conn: sqlite3.Connection,
    *,
    queued: int,
    owned: int,
    skipped: int,
    no_match: int,
    gave_up: int,
) -> None:
    conn.execute(
        "INSERT INTO runs (run_date, queued, owned, skipped, no_match, gave_up) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (_now(), queued, owned, skipped, no_match, gave_up),
    )


def all_rows(conn: sqlite3.Connection) -> list[Row]:
    return [
        Row(**dict(r))
        for r in conn.execute(
            "SELECT source, title, author, status, retry_count, last_attempted "
            "FROM books ORDER BY source, status, title"
        )
    ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
