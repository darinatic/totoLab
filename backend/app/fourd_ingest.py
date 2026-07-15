"""Fetch + parse 4D draws from the official Singapore Pools results archive.

Every draw is addressable by number via the base64 `sppl=DrawNumber=<n>` query
param, and the whole history (draw 1 = 1986 through the latest) is available. We
seed from a bundled `fourd_seed.csv` (a backfilled range) and keep it current
with a polite low-frequency refresh of the most recent draws. Idempotent.
"""
from __future__ import annotations

import base64
import csv
import re
import time
from typing import List, Optional, Sequence, Tuple

import requests

from . import fourd_config as fc
from . import fourd_db as db

FourRow = Tuple[int, str, str, str]  # draw_no, draw_date, prize_code, digit

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
_TAG_RE = re.compile(r"<[^>]+>")
_BASE = "https://www.singaporepools.com.sg/en/product/pages/4d_results.aspx"
_DRAW_LIST = ("https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/"
              "fourd_result_draw_list_en.html")
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", html))


def _url(draw_no: Optional[int]) -> str:
    if draw_no is None:
        return _BASE
    sppl = base64.b64encode(f"DrawNumber={draw_no}".encode()).decode()
    return f"{_BASE}?sppl={sppl}"


def parse_page(html: str) -> Optional[dict]:
    """Parse one results page into {draw_no, draw_date (ISO), entries:[(code,digit)]}."""
    i = html.find("Draw No")
    if i < 0:
        return None
    dno_m = re.search(r"Draw No\.?\s*(\d+)", _text(html[i:i + 60]))
    date_m = re.search(r"(\d{1,2}) ([A-Z][a-z]{2}) (\d{4})", _text(html[max(0, i - 160):i]))
    if not dno_m or not date_m:
        return None
    day, mon, year = date_m.groups()
    if mon not in _MONTHS:
        return None
    date_iso = f"{year}-{_MONTHS[mon]:02d}-{int(day):02d}"

    seg = _text(html[i:i + 2500])

    def grab(label: str) -> Optional[str]:
        m = re.search(label + r"\s*(\d{4})", seg)
        return m.group(1) if m else None

    first, second, third = grab("1st Prize"), grab("2nd Prize"), grab("3rd Prize")

    def tbody_nums(keyword: str) -> List[str]:
        m = re.search(r"tbody[^>]*" + keyword + r"[^>]*>(.*?)</tbody>", html, re.S | re.I)
        return re.findall(r">(\d{4})<", m.group(1)) if m else []

    starters, consolations = tbody_nums("Start"), tbody_nums("Consol")
    if not (first and second and third) or len(starters) != 10 or len(consolations) != 10:
        return None
    entries = ([("1", first), ("2", second), ("3", third)]
               + [("S", s) for s in starters] + [("C", c) for c in consolations])
    return {"draw_no": int(dno_m.group(1)), "draw_date": date_iso, "entries": entries}


def _fetch_html(draw_no: Optional[int], timeout: int = 20) -> str:
    resp = requests.get(_url(draw_no), headers={"User-Agent": _UA}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def draw_list() -> List[int]:
    """All draw numbers currently in the official archive (newest first)."""
    resp = requests.get(_DRAW_LIST, headers={"User-Agent": _UA}, timeout=20)
    resp.raise_for_status()
    opts = re.findall(r"value=[\"']([0-9]{3,6})[\"']", resp.text)
    return [int(v) for v in opts]


def latest_draw_number() -> Optional[int]:
    """The most recent draw number, from the official draw-list archive file."""
    nums = draw_list()
    return nums[0] if nums else None


def _rows_for(parsed: dict) -> List[FourRow]:
    return [(parsed["draw_no"], parsed["draw_date"], code, digit)
            for code, digit in parsed["entries"]]


def fetch_recent(limit: int = 5, delay: float = 0.4) -> List[FourRow]:
    """Fetch the newest `limit` draws (descending from the latest)."""
    latest = latest_draw_number()
    if latest is None:
        return []
    rows: List[FourRow] = []
    for n in range(latest, max(0, latest - limit), -1):
        try:
            parsed = parse_page(_fetch_html(n))
        except requests.RequestException:
            continue
        if parsed:
            rows.extend(_rows_for(parsed))
        time.sleep(delay)
    return rows


def backfill(count: int, until: Optional[int] = None, delay: float = 0.4,
             log_every: int = 100) -> List[FourRow]:
    """Fetch draws descending from the latest for `count` draws (or down to `until`)."""
    latest = latest_draw_number()
    if latest is None:
        return []
    stop = until if until is not None else latest - count + 1
    rows: List[FourRow] = []
    done = 0
    for n in range(latest, max(0, stop) - 1, -1):
        try:
            parsed = parse_page(_fetch_html(n))
            if parsed:
                rows.extend(_rows_for(parsed))
        except requests.RequestException:
            pass
        done += 1
        if log_every and done % log_every == 0:
            print(f"  ...{done} draws fetched (at draw {n})", flush=True)
        time.sleep(delay)
    return rows


def write_seed_csv(rows: Sequence[FourRow], path=None) -> int:
    path = path or fc.FOURD_SEED_CSV
    uniq = {(r[1], r[3]): r for r in rows}  # dedupe by (date, digit)
    ordered = sorted(uniq.values(), key=lambda r: (r[1], r[2], r[3]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["draw_no", "draw_date", "prize_code", "digit"])
        for r in ordered:
            w.writerow(r)
    return len({r[1] for r in ordered})  # number of draws


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


def refresh(limit: int = 5, db_path=None) -> int:
    return db.upsert_rows(fetch_recent(limit), db_path)


def update_seed_csv(limit: int = 5, path=None) -> int:
    """Merge the most recent draws into the seed CSV (used by the GitHub Action)."""
    path = path or fc.FOURD_SEED_CSV
    existing = {(r[1], r[3]): r for r in load_seed_csv(path)}
    before = len({r[1] for r in existing.values()})
    for row in fetch_recent(limit):
        existing[(row[1], row[3])] = row
    write_seed_csv(list(existing.values()), path)
    return len({r[1] for r in existing.values()}) - before


if __name__ == "__main__":  # python -m app.fourd_ingest [--backfill N | --update-csv]
    import argparse
    p = argparse.ArgumentParser(description="4D data ingest (official Singapore Pools)")
    p.add_argument("--backfill", type=int, help="backfill the latest N draws into the seed CSV")
    p.add_argument("--update-csv", action="store_true")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--delay", type=float, default=0.4)
    args = p.parse_args()
    if args.backfill:
        rows = backfill(args.backfill, delay=args.delay)
        n = write_seed_csv(rows)
        print(f"Backfilled {n} draws into {fc.FOURD_SEED_CSV}")
    elif args.update_csv:
        print(f"Added {update_seed_csv(limit=args.limit)} new 4D draws")
    else:
        print(f"Seeded {seed_if_empty()} rows; {db.count_draws()} draws")
