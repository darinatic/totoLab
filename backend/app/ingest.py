"""Fetch + parse Toto draws and seed the database.

Data comes from a community aggregator (lottolyzer), NOT scraped from Singapore
Pools directly, whose Terms of Service prohibit scraping. Fetches are polite and
low-frequency (draws happen only twice a week) and upserts are idempotent.
"""
from __future__ import annotations

import csv
import re
from typing import List, Sequence, Tuple

import requests

from . import config, db

DrawRow = Tuple[int, str, int, int, int, int, int, int, int]

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def parse_html(html: str) -> List[DrawRow]:
    """Parse one aggregator summary page into draw rows.

    Table columns: Draw | Date | Winning No. | Addl No. | ...trailing stats.
    Only well-formed 6/49 rows are returned.
    """
    out: List[DrawRow] = []
    for raw_row in _ROW_RE.findall(html):
        cells = [
            _TAG_RE.sub(" ", c).strip() for c in _CELL_RE.findall(raw_row)
        ]
        if len(cells) < 4 or not re.match(r"^\d+$", cells[0]):
            continue
        nums = [int(x) for x in re.findall(r"\d+", cells[2])]
        add = re.findall(r"\d+", cells[3])
        if len(nums) != 6 or not add:
            continue
        nums.sort()
        out.append((int(cells[0]), cells[1], *nums, int(add[0])))
    return out


def fetch_pages(pages: Sequence[int], timeout: int = 20) -> List[DrawRow]:
    """Fetch and parse the given aggregator pages. Deduplicates by draw_no."""
    seen: dict[int, DrawRow] = {}
    headers = {"User-Agent": config.SOURCE_USER_AGENT}
    for page in pages:
        url = config.SOURCE_URL_TEMPLATE.format(page=page)
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        for row in parse_html(resp.text):
            seen[row[0]] = row
    return sorted(seen.values(), key=lambda r: r[0])


def load_seed_csv(path=None) -> List[DrawRow]:
    path = path or config.SEED_CSV
    rows: List[DrawRow] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                (
                    int(r["draw_no"]),
                    r["draw_date"],
                    int(r["n1"]), int(r["n2"]), int(r["n3"]),
                    int(r["n4"]), int(r["n5"]), int(r["n6"]),
                    int(r["additional"]),
                )
            )
    return sorted(rows, key=lambda x: x[0])


def seed_if_empty(db_path=None) -> int:
    """Initialise the DB and load the bundled seed CSV if the table is empty.

    Returns the number of rows seeded (0 if the DB already had data).
    """
    db.init_db(db_path)
    if db.count_draws(db_path) > 0:
        return 0
    rows = load_seed_csv()
    return db.upsert_draws(rows, db_path)


def refresh(pages: Sequence[int] = (1, 2), db_path=None) -> int:
    """Fetch the most recent aggregator pages and upsert. Returns rows written."""
    rows = fetch_pages(pages)
    return db.upsert_draws(rows, db_path)


def update_seed_csv(pages: Sequence[int] = (1, 2), path=None) -> int:
    """Merge freshly fetched draws into the seed CSV. Returns count of NEW draws.

    Used by the scheduled GitHub Action: it commits the updated CSV, which is the
    source of truth the app reseeds from on deploy.
    """
    path = path or config.SEED_CSV
    existing = {r[0]: r for r in load_seed_csv(path)}
    before = len(existing)
    for row in fetch_pages(pages):
        existing[row[0]] = row
    rows = sorted(existing.values(), key=lambda r: r[0])
    with open(path, "w", newline="", encoding="utf-8") as fo:
        import csv as _csv
        w = _csv.writer(fo)
        w.writerow(["draw_no", "draw_date", "n1", "n2", "n3", "n4", "n5", "n6", "additional"])
        for r in rows:
            w.writerow(r)
    return len(existing) - before


if __name__ == "__main__":  # python -m app.ingest [--update-csv]
    import argparse

    parser = argparse.ArgumentParser(description="Toto data ingest")
    parser.add_argument("--update-csv", action="store_true",
                        help="fetch recent draws and merge into the seed CSV")
    parser.add_argument("--pages", type=int, default=2, help="aggregator pages to fetch")
    args = parser.parse_args()

    if args.update_csv:
        added = update_seed_csv(pages=tuple(range(1, args.pages + 1)))
        print(f"Added {added} new draws to {config.SEED_CSV}")
    else:
        n = seed_if_empty()
        print(f"Seeded {n} draws; total now {db.count_draws()}")
