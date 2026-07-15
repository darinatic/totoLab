"""Fetch + parse 4D draws and seed the database.

Seed is the bundled `fourd_seed.csv` (real prize-coded history 1992-2018 from the
nwfxyz/4D_analytics dataset). Ongoing refresh parses the current aggregator
(nestia), which exposes recent draws with per-draw pages, each showing the full
23 prize-categorised numbers. Polite and idempotent.
"""
from __future__ import annotations

import csv
import json
import re
from typing import List, Sequence, Tuple

import requests

from . import fourd_config as fc
from . import fourd_db as db

FourRow = Tuple[int, str, str, str]  # draw_no, draw_date, prize_code, digit

_TAG_RE = re.compile(r"<[^>]+>")
_FOURD_RE = re.compile(r"\b\d{4}\b")


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", html))


def parse_draw_page(html: str) -> List[Tuple[str, str]]:
    """Parse one draw page into [(prize_code, digit), ...] (23 entries, or fewer)."""
    text = _text(html)
    out: List[Tuple[str, str]] = []

    def after(label: str, n: int) -> List[str]:
        idx = text.find(label)
        if idx < 0:
            return []
        return _FOURD_RE.findall(text[idx + len(label): idx + len(label) + 30 + n * 8])[:n]

    for label, code in (("1st", "1"), ("2nd", "2"), ("3rd", "3")):
        vals = after(label, 1)
        if vals:
            out.append((code, vals[0]))
    for d in after("Starter Prizes", 10):
        out.append(("S", d))
    for d in after("Consolation Prizes", 10):
        out.append(("C", d))
    return out


def parse_all_draws(html: str) -> List[dict]:
    """Extract the ALL_DRAWS list (draw_id + ISO date + link) from the /4d page."""
    m = re.search(r"ALL_DRAWS\s*=\s*(\[.*?\])", html, re.S)
    if not m:
        return []
    try:
        raw = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    draws = []
    for d in raw:
        link = d.get("link", "")
        date_m = re.search(r"\d{4}-\d{2}-\d{2}", link)
        if date_m and d.get("draw_id"):
            draws.append({"draw_id": int(d["draw_id"]), "date": date_m.group(0), "link": link})
    return draws


def fetch_recent(limit: int = 3, timeout: int = 20) -> List[FourRow]:
    """Fetch the newest `limit` draws (each via its own page). Returns long rows."""
    headers = {"User-Agent": fc.SOURCE_USER_AGENT}
    index = requests.get(fc.SOURCE_URL, headers=headers, timeout=timeout)
    index.raise_for_status()
    rows: List[FourRow] = []
    for meta in parse_all_draws(index.text)[:limit]:
        url = "https://lottery.nestia.com" + meta["link"]
        page = requests.get(url, headers=headers, timeout=timeout)
        page.raise_for_status()
        entries = parse_draw_page(page.text)
        # only accept the complete standard-format draw
        if len(entries) == fc.NUMBERS_PER_DRAW:
            for code, digit in entries:
                rows.append((meta["draw_id"], meta["date"], code, digit))
    return rows


def load_seed_csv(path=None) -> List[FourRow]:
    path = path or fc.FOURD_SEED_CSV
    rows: List[FourRow] = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((int(r["draw_no"]), r["draw_date"], r["prize_code"],
                         str(r["digit"]).zfill(4)))
    return rows


def seed_if_empty(db_path=None) -> int:
    db.init_db(db_path)
    if db.count_rows(db_path) > 0:
        return 0
    return db.upsert_rows(load_seed_csv(), db_path)


def refresh(limit: int = 3, db_path=None) -> int:
    return db.upsert_rows(fetch_recent(limit), db_path)


def update_seed_csv(limit: int = 5, path=None) -> int:
    """Merge freshly fetched draws into the seed CSV (used by the GitHub Action)."""
    path = path or fc.FOURD_SEED_CSV
    existing = {(r[1], r[3]): r for r in load_seed_csv(path)}  # keyed (date, digit)
    before = len(existing)
    for row in fetch_recent(limit):
        existing[(row[1], row[3])] = row
    rows = sorted(existing.values(), key=lambda r: (r[1], r[2], r[3]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["draw_no", "draw_date", "prize_code", "digit"])
        for r in rows:
            w.writerow(r)
    return len(existing) - before


if __name__ == "__main__":  # python -m app.fourd_ingest [--update-csv]
    import argparse
    p = argparse.ArgumentParser(description="4D data ingest")
    p.add_argument("--update-csv", action="store_true")
    p.add_argument("--limit", type=int, default=5)
    args = p.parse_args()
    if args.update_csv:
        print(f"Added {update_seed_csv(limit=args.limit)} new 4D draws")
    else:
        n = seed_if_empty()
        print(f"Seeded {n} rows; {db.count_draws()} draws")
