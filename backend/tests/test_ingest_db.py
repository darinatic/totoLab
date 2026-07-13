"""Ingest parsing + DB upsert idempotency."""
from app import db, ingest

SAMPLE_HTML = """
<table>
<tr><td>Draw</td><td>Date</td><td>Winning No.</td><td>Addl No.</td><td>x</td></tr>
<tr><td>4198</td><td>2026-07-09</td><td>23,27,31,38,42,47</td><td>29</td><td>foo</td></tr>
<tr><td>4197</td><td>2026-07-06</td><td>8,25,34,37,39,46</td><td>44</td><td>bar</td></tr>
<tr><td>bad</td><td>row</td><td>1,2,3</td><td></td><td></td></tr>
</table>
"""


def test_parse_html_extracts_valid_rows():
    rows = ingest.parse_html(SAMPLE_HTML)
    assert len(rows) == 2
    first = rows[0]
    assert first[0] == 4198
    assert first[1] == "2026-07-09"
    assert list(first[2:8]) == [23, 27, 31, 38, 42, 47]  # sorted mains
    assert first[8] == 29


def test_upsert_is_idempotent(tmp_path):
    dbp = tmp_path / "t.db"
    db.init_db(dbp)
    rows = ingest.parse_html(SAMPLE_HTML)
    db.upsert_draws(rows, dbp)
    db.upsert_draws(rows, dbp)  # again
    assert db.count_draws(dbp) == 2


def test_seed_loads_bundled_csv(tmp_path):
    dbp = tmp_path / "t.db"
    n = ingest.seed_if_empty(dbp)
    assert n > 100
    assert ingest.seed_if_empty(dbp) == 0  # already seeded -> no-op

    df = db.load_draws(dbp)
    # all modelled numbers valid and 6 distinct per draw
    for row in df["numbers"]:
        assert len(set(row)) == 6
        assert all(1 <= n <= 49 for n in row)
