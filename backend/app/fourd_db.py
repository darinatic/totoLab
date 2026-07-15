"""SQLite storage for 4D draws + a per-draw pandas loader.

Draws are stored long-format (one row per winning number); the loader pivots
them into a per-draw DataFrame that the analysis / strategy / backtest modules
consume.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterable, Iterator, Sequence

import pandas as pd

from . import fourd_config as fc

SCHEMA = """
CREATE TABLE IF NOT EXISTS fourd_draws (
    draw_no    INTEGER NOT NULL,
    draw_date  TEXT NOT NULL,
    prize_code TEXT NOT NULL,
    digit      TEXT NOT NULL,
    PRIMARY KEY (draw_date, digit)
);
CREATE INDEX IF NOT EXISTS idx_fourd_date ON fourd_draws(draw_date);
"""


@contextmanager
def connect(db_path=None) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path or fc.FOURD_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path=None) -> None:
    fc.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def upsert_rows(rows: Iterable[Sequence], db_path=None) -> int:
    """Insert-or-replace long-format rows: (draw_no, draw_date, prize_code, digit)."""
    rows = list(rows)
    if not rows:
        return 0
    with connect(db_path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO fourd_draws "
            "(draw_no, draw_date, prize_code, digit) VALUES (?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def count_rows(db_path=None) -> int:
    with connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM fourd_draws").fetchone()[0]


def count_draws(db_path=None) -> int:
    with connect(db_path) as conn:
        return conn.execute("SELECT COUNT(DISTINCT draw_date) FROM fourd_draws").fetchone()[0]


def load_fourd_draws(db_path=None, era_only: bool = True) -> pd.DataFrame:
    """Return one row per draw (oldest->newest) with convenience columns.

    Columns: draw_no, draw_date, first, second, third, starters (10), consolations
    (10), all_numbers (23), first_digits (4 ints from the First prize).
    """
    with connect(db_path) as conn:
        raw = pd.read_sql_query(
            "SELECT draw_no, draw_date, prize_code, digit FROM fourd_draws "
            "ORDER BY draw_date ASC",
            conn,
        )
    if raw.empty:
        return raw
    if era_only:
        raw = raw[raw["draw_date"] >= fc.ERA_START]

    records = []
    for (draw_no, draw_date), g in raw.groupby(["draw_no", "draw_date"], sort=True):
        by_code = {c: list(g[g["prize_code"] == c]["digit"]) for c in fc.PRIZE_CODES}
        first = by_code["1"][0] if by_code["1"] else None
        if first is None:
            continue
        all_numbers = [d for c in fc.PRIZE_CODES for d in by_code[c]]
        records.append({
            "draw_no": int(draw_no),
            "draw_date": draw_date,
            "first": first,
            "second": by_code["2"][0] if by_code["2"] else None,
            "third": by_code["3"][0] if by_code["3"] else None,
            "starters": by_code["S"],
            "consolations": by_code["C"],
            "all_numbers": all_numbers,
            "first_digits": [int(ch) for ch in first],
        })
    df = pd.DataFrame(records).sort_values("draw_date").reset_index(drop=True)
    return df
