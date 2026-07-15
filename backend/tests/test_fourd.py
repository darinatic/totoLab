"""Tests for the 4D game modules."""
import numpy as np
import pandas as pd
import pytest

from app import (fourd_analysis as fa, fourd_backtest as fbt, fourd_config as fc,
                 fourd_db as fdb, fourd_fairness as ff, fourd_ingest as ing,
                 fourd_ml as fml, fourd_strategies as fs)
from tests.conftest import _make_fourd_df

# Minimal HTML mirroring the official Singapore Pools results-page structure.
SAMPLE_DRAW_HTML = """
<div>Sun, 12 Jul 2026 <span>Draw No. 5508</span>
<div>1st Prize 1234</div><div>2nd Prize 5678</div><div>3rd Prize 9012</div>
<div>Starter Prizes</div>
<tbody class="tbodyStarter"><tr>
<td>1111</td><td>2222</td><td>3333</td><td>4444</td><td>5555</td>
<td>6666</td><td>7777</td><td>8888</td><td>9999</td><td>0000</td></tr></tbody>
<div>Consolation Prizes</div>
<tbody class="tbodyConsolation"><tr>
<td>1010</td><td>2020</td><td>3030</td><td>4040</td><td>5050</td>
<td>6060</td><td>7070</td><td>8080</td><td>9090</td><td>0101</td></tr></tbody>
</div>
"""


# --- ingest / db ---
def test_parse_page():
    parsed = ing.parse_page(SAMPLE_DRAW_HTML)
    assert parsed["draw_no"] == 5508
    assert parsed["draw_date"] == "2026-07-12"
    entries = parsed["entries"]
    assert len(entries) == 23
    comp = {c: sum(1 for x, _ in entries if x == c) for c in fc.PRIZE_CODES}
    assert comp == {"1": 1, "2": 1, "3": 1, "S": 10, "C": 10}
    assert entries[0] == ("1", "1234")


def test_parse_page_rejects_incomplete():
    assert ing.parse_page("<div>no draw here</div>") is None


def test_seed_and_load(tmp_path):
    dbp = tmp_path / "f.db"
    n = ing.seed_if_empty(dbp)
    assert n > 1000
    assert ing.seed_if_empty(dbp) == 0  # idempotent
    df = fdb.load_fourd_draws(dbp)
    r = df.iloc[-1]
    assert len(r["all_numbers"]) == 23
    assert len(r["first_digits"]) == 4
    assert all(0 <= d <= 9 for d in r["first_digits"])


# --- analysis (hand-checked) ---
def _tiny():
    rows = [
        {"draw_no": 1, "draw_date": "2020-01-01", "first": "1234",
         "second": "0000", "third": "1111",
         "starters": [f"{i:04d}" for i in range(10)],
         "consolations": [f"{i:04d}" for i in range(10, 20)],
         "all_numbers": ["1234", "0000", "1111"] + [f"{i:04d}" for i in range(20)],
         "first_digits": [1, 2, 3, 4]},
        {"draw_no": 2, "draw_date": "2020-01-04", "first": "1299",
         "second": "5555", "third": "6666",
         "starters": [f"{i:04d}" for i in range(30, 40)],
         "consolations": [f"{i:04d}" for i in range(40, 50)],
         "all_numbers": ["1299", "5555", "6666"] + [f"{i:04d}" for i in range(30, 50)],
         "first_digits": [1, 2, 9, 9]},
    ]
    return pd.DataFrame(rows)


def test_digit_sum_and_repeats():
    df = _tiny()
    s = fa.digit_sum_distribution(df)
    assert s["min"] == 10 and s["max"] == 21  # 1+2+3+4, 1+2+9+9
    rep = fa.repeats_from_previous(df)
    assert rep["expected_mean"] == 0.4
    # first prizes 1234 vs 1299 share positions 0,1 -> 2 matches
    d = {x["matches"]: x["count"] for x in rep["distribution"]}
    assert d[2] == 1


def test_digit_frequency_positions():
    df = _tiny()
    freq = fa.digit_frequency_by_position(df, "first")
    assert len(freq) == 4
    pos0 = {r["digit"]: r["count"] for r in freq[0]["digits"]}
    assert pos0[1] == 2  # both first prizes start with 1


def test_number_detail():
    df = _tiny()
    d = fa.number_detail(df, "1234")
    assert d["appearances"] == 1
    assert d["digit_sum"] == 10


# --- strategies ---
@pytest.mark.parametrize("key", list(fs.STRATEGIES.keys()))
def test_strategy_valid_number(fourd_df, key):
    res = fs.predict(key, fourd_df, seed=1, sets=3)
    assert len(res["sets"]) == 3
    for num in res["sets"]:
        assert len(num) == 4 and num.isdigit()  # 4 digits, repetition allowed


def test_strategies_reproducible(fourd_df):
    a = fs.predict("frequency", fourd_df, seed=5)
    b = fs.predict("frequency", fourd_df, seed=5)
    assert a["sets"] == b["sets"]


# --- ML ---
@pytest.mark.parametrize("key", ["ml_gbm", "ml_logistic", "ml_mlp"])
def test_ml_valid_number(fourd_df, key):
    res = fs.predict(key, fourd_df, seed=0, sets=2)
    assert res["strategy"] == key
    for num in res["sets"]:
        assert len(num) == 4 and num.isdigit()


# --- fairness detection ---
def test_fairness_passes_fair_data(fourd_df):
    assert ff.run_all(fourd_df)["overall_passes"] is True


def test_fairness_flags_biased_data():
    biased = _make_fourd_df(n_draws=300, bias_pos0=7)
    res = ff.run_all(biased)
    # position-0 always 7 -> chi-square (pooled and per-position) must flag
    assert res["overall_passes"] is False


# --- backtest ---
def test_backtest_honest_and_no_leakage(fourd_df, monkeypatch):
    seen = []
    orig = fs.STRATEGIES["random"]

    def spy(df, rng):
        seen.append(len(df))
        return orig(df, rng)

    monkeypatch.setitem(fs.STRATEGIES, "random", spy)
    res = fbt.run(fourd_df, test_size=40, include_ml=False, seed=0)
    assert res["theoretical_random"] == 0.4
    assert res["any_beats_random"] is False
    # history strictly increasing and always < total
    assert seen == sorted(seen) and all(l < len(fourd_df) for l in seen)


def test_backtest_detects_skill(monkeypatch):
    # dataset where the First prize is always 1234; a copycat must beat 0.4
    df = _make_fourd_df(n_draws=120)
    df = df.copy()
    df["first"] = "1234"
    df["first_digits"] = [[1, 2, 3, 4]] * len(df)
    monkeypatch.setitem(fs.STRATEGIES, "copy",
                        lambda d, rng: {"number": d.iloc[-1]["first"]})
    monkeypatch.setitem(fs.STRATEGY_LABELS, "copy", "Copycat")
    monkeypatch.setitem(fs.STRATEGY_INDEX, "copy", 99)
    res = fbt.run(df, test_size=40, include_ml=False, seed=0)
    copy = next(r for r in res["results"] if r["strategy"] == "copy")
    assert copy["mean_matches"] == 4.0
    assert copy["beats_random"] is True
