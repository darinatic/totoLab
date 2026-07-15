"""Configuration and game constants for Singapore 4D.

4D is positional: a draw yields 23 winning 4-digit numbers (1 First, 1 Second,
1 Third, 10 Starter, 10 Consolation). Each number is 4 independent digits 0-9
(repetition allowed, order matters). We analyse all 23 winning numbers and
predict/score against the First prize.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import config  # reuse shared paths/CORS

# --- Game constants ---
POSITIONS = 4
N_DIGITS = 10
DIGITS = list(range(N_DIGITS))
PRIZE_CODES = ["1", "2", "3", "S", "C"]   # First, Second, Third, Starter, Consolation
TOP_CODES = ["1", "2", "3"]
NUMBERS_PER_DRAW = 23

# Standard 1+1+1+10+10 format has been consistent since 1992; older draws differ.
ERA_START = "1992-01-01"

# A random 4-digit guess matches the First prize on 4 * 1/10 = 0.4 positions on
# average - the direct analogue of Toto's 0.735 expected matches.
EXPECTED_RANDOM_DIGIT_MATCHES = POSITIONS * (1 / N_DIGITS)
FIRST_PRIZE_ODDS = "1 in 10,000"

# --- Paths ---
DATA_DIR = config.DATA_DIR
FOURD_SEED_CSV = DATA_DIR / "fourd_seed.csv"
FOURD_DB_PATH = Path(os.environ.get("TOTO_FOURD_DB_PATH", DATA_DIR / "fourd.db"))
FOURD_PRECOMPUTE_BACKTEST = Path(os.environ.get(
    "TOTO_FOURD_PRECOMPUTE_BACKTEST",
    config.BASE_DIR.parent / "frontend" / "public" / "precomputed" / "4d_backtest.json",
))

# --- Data source (current aggregator for ongoing refresh) ---
SOURCE_URL = "https://lottery.nestia.com/4d"
SOURCE_USER_AGENT = config.SOURCE_USER_AGENT

DISCLAIMER = (
    "Singapore 4D draws are independent random events. No method can predict "
    "future draws better than chance; matching the First prize is 1 in 10,000 "
    "and the expected value of a bet is negative."
)
