"""SQLite storage for draws + a pandas loader used by every analysis module."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterable, Iterator, Sequence

import pandas as pd

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS draws (
    draw_no   INTEGER PRIMARY KEY,
    draw_date TEXT NOT NULL,
    n1 INTEGER NOT NULL,
    n2 INTEGER NOT NULL,
    n3 INTEGER NOT NULL,
    n4 INTEGER NOT NULL,
    n5 INTEGER NOT NULL,
    n6 INTEGER NOT NULL,
    additional INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_draws_date ON draws(draw_date);
"""


@contextmanager
def connect(db_path=None) -> Iterator[sqlite3.Connection]:
    path = str(db_path or config.DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path=None) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def upsert_draws(rows: Iterable[Sequence], db_path=None) -> int:
    """Insert-or-replace draws. `rows` = (draw_no, draw_date, n1..n6, additional).

    Idempotent: re-running with the same data changes nothing. Returns the
    number of rows written.
    """
    rows = list(rows)
    if not rows:
        return 0
    with connect(db_path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO draws "
            "(draw_no, draw_date, n1, n2, n3, n4, n5, n6, additional) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def count_draws(db_path=None) -> int:
    with connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0]


def load_draws(db_path=None, era_only: bool = True) -> pd.DataFrame:
    """Return draws as a DataFrame sorted oldest->newest.

    Adds convenience columns: `numbers` (sorted list of the 6 mains) and
    `all_numbers` (mains + additional). When `era_only`, restricts to the
    current 6/49 era so modelling is apples-to-apples.
    """
    with connect(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM draws ORDER BY draw_no ASC", conn)
    if df.empty:
        return df
    if era_only:
        df = df[df["draw_date"] >= config.ERA_6_49_START].reset_index(drop=True)
    num_cols = ["n1", "n2", "n3", "n4", "n5", "n6"]
    df["numbers"] = df[num_cols].values.tolist()
    df["all_numbers"] = df[num_cols + ["additional"]].values.tolist()
    return df
