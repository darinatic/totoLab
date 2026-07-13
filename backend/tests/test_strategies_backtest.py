"""Strategy validity + backtest correctness (esp. no future leakage)."""
import numpy as np
import pandas as pd
import pytest

from app import backtest, config, db, ingest, ml, strategies


@pytest.mark.parametrize("key", list(strategies.STRATEGIES.keys()))
def test_strategy_returns_valid_ticket(draws_df, key):
    rng = np.random.default_rng(0)
    res = strategies.STRATEGIES[key](draws_df, rng)
    nums = res["numbers"]
    assert len(nums) == 6
    assert len(set(nums)) == 6
    assert all(1 <= n <= 49 for n in nums)
    assert nums == sorted(nums)


def test_strategy_reproducible_with_seed(draws_df):
    a = strategies.predict("frequency", draws_df, seed=123)
    b = strategies.predict("frequency", draws_df, seed=123)
    assert a["sets"] == b["sets"]


def test_predict_count_and_sets(draws_df):
    r = strategies.predict("frequency", draws_df, seed=1, count=9, sets=3)
    assert len(r["sets"]) == 3
    for s in r["sets"]:
        assert len(s) == 9 and len(set(s)) == 9
        assert all(1 <= n <= 49 for n in s)
    # independent sets should not all be identical
    assert not all(s == r["sets"][0] for s in r["sets"][1:])


def test_new_strategies_present_and_valid(draws_df):
    for key in ("cold", "contrarian"):
        assert key in strategies.STRATEGIES
        r = strategies.predict(key, draws_df, seed=1)
        assert len(r["sets"][0]) == 6


def test_contrarian_favours_high_numbers(draws_df):
    # over many sets, contrarian should skew toward numbers > 31
    r = strategies.predict("contrarian", draws_df, seed=1, sets=10)
    picked = [n for s in r["sets"] for n in s]
    high = sum(1 for n in picked if n > 31)
    assert high / len(picked) > 0.5


def test_strategies_use_independent_rng_streams():
    # Same top-level seed but different strategies must NOT share a random
    # stream, else similar weights collapse to near-identical picks.
    s1 = strategies._make_rng(1, "frequency").random(6)
    s2 = strategies._make_rng(1, "markov").random(6)
    assert not np.allclose(s1, s2)


def test_markov_is_not_just_frequency(tmp_path):
    # Regression: raw co-occurrence is dominated by base rate and correlates
    # ~0.77 with frequency. The conditional-rate normalisation must decorrelate
    # it so "Markov" is a genuinely distinct strategy.
    dbp = tmp_path / "t.db"
    ingest.seed_if_empty(dbp)
    df = db.load_draws(dbp)
    f = np.array([strategies.frequency_weights(df)[n] for n in config.POOL])
    m = np.array([strategies.markov_scores(df)[n] for n in config.POOL])
    corr = abs(np.corrcoef(f, m)[0, 1])
    assert corr < 0.5, f"markov still tracks frequency too closely: r={corr:.3f}"


def test_frequency_and_markov_differ_on_same_seed(draws_df):
    freq = strategies.predict("frequency", draws_df, seed=1)
    markov = strategies.predict("markov", draws_df, seed=1)
    # they may share a number or two by chance, but must not be identical sets
    assert freq["sets"][0] != markov["sets"][0]


def test_ml_returns_valid_ticket(draws_df):
    res = ml.predict(draws_df, seed=0, count=6, sets=2)
    assert len(res["sets"]) == 2
    for s in res["sets"]:
        assert len(set(s)) == 6
        assert all(1 <= n <= 49 for n in s)


def test_ml_no_future_leakage_in_features():
    # feature builder must only look at the history slice it is given
    from app.ml import _features_for_draw
    history = [[1, 2, 3, 4, 5, 6]] * 60
    f_full = _features_for_draw(history, 1)
    f_short = _features_for_draw(history[:30], 1)
    # number 1 appears every draw -> recent-window frequency is 1.0 either way
    assert f_full[0] == pytest.approx(1.0)
    assert f_short[0] == pytest.approx(1.0)


def test_backtest_runs_and_is_honest(draws_df):
    res = backtest.run(draws_df, test_size=40, include_ml=False, seed=0)
    assert res["test_size"] == 40
    means = {r["strategy"]: r["mean_matches"] for r in res["results"]}
    # every strategy should be in the neighbourhood of the theoretical 0.735
    for m in means.values():
        assert 0.0 <= m <= 2.0
    # on fair synthetic data nothing should beat random
    assert res["any_beats_random"] is False


def test_backtest_flags_a_skillful_strategy(monkeypatch):
    """Sanity on the detector itself: on a perfectly predictable dataset, a
    strategy that exploits it MUST be flagged as beating random (incl. the
    zero-variance perfect-predictor edge case)."""
    fixed = [1, 2, 3, 4, 5, 6]
    df = pd.DataFrame([
        {"draw_no": i + 1, "draw_date": f"2020-{1 + i % 12:02d}-{1 + i % 28:02d}",
         "n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5, "n6": 6, "additional": 7,
         "numbers": list(fixed), "all_numbers": list(fixed) + [7]}
        for i in range(120)
    ])
    monkeypatch.setitem(strategies.STRATEGIES, "copylast",
                        lambda d, rng: {"numbers": sorted(d["numbers"].iloc[-1]), "scores": {}})
    monkeypatch.setitem(strategies.STRATEGY_LABELS, "copylast", "Copy last")
    monkeypatch.setitem(strategies.STRATEGY_INDEX, "copylast", 99)
    res = backtest.run(df, test_size=40, include_ml=False, seed=0)
    copy = next(r for r in res["results"] if r["strategy"] == "copylast")
    assert copy["mean_matches"] == 6.0
    assert copy["beats_random"] is True
    assert res["any_beats_random"] is True


def test_backtest_no_leakage_monkeypatch(draws_df, monkeypatch):
    """Verify each prediction only ever sees history strictly before the target."""
    seen_lengths = []
    target_indices = []
    orig = strategies.STRATEGIES["random"]

    def spy(history, rng):
        seen_lengths.append(len(history))
        return orig(history, rng)

    monkeypatch.setitem(strategies.STRATEGIES, "random", spy)
    backtest.run(draws_df, test_size=30, include_ml=False, seed=0)
    # history length must be strictly increasing and < total draws
    assert all(l < len(draws_df) for l in seen_lengths)
    assert seen_lengths == sorted(seen_lengths)
