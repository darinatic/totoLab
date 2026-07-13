"""Central configuration and Toto game constants."""
from __future__ import annotations

import os
from pathlib import Path

# --- Game constants (current 6/49 format) ---
POOL_MIN = 1
POOL_MAX = 49
PICK = 6                      # numbers drawn (excluding the additional number)
POOL = list(range(POOL_MIN, POOL_MAX + 1))
POOL_SIZE = POOL_MAX - POOL_MIN + 1  # 49

# The current 6/49 era. Draws before this are a different game format and are
# excluded from modelling / fairness tests to keep the analysis apples-to-apples.
ERA_6_49_START = "2014-10-01"

# Expected matches for a random 6/49 ticket against the 6 drawn numbers:
#   6 * (6/49) = 0.7346...  (linearity of expectation)
EXPECTED_RANDOM_MATCHES = PICK * PICK / POOL_SIZE

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
DATA_DIR = BASE_DIR / "data"
SEED_CSV = DATA_DIR / "seed_draws.csv"
DB_PATH = Path(os.environ.get("TOTO_DB_PATH", DATA_DIR / "toto.db"))

# Precomputed default backtest, served as a static asset so the (slow) walk-forward
# backtest never runs on first page load. Lives in the frontend's public/ dir so it
# ships with the SPA; regenerated whenever the seed data changes.
PRECOMPUTE_BACKTEST = Path(os.environ.get(
    "TOTO_PRECOMPUTE_BACKTEST",
    BASE_DIR.parent / "frontend" / "public" / "precomputed" / "backtest.json",
))

# --- Data source (ToS-safe community aggregator; NOT Singapore Pools directly) ---
SOURCE_URL_TEMPLATE = (
    "https://en.lottolyzer.com/history/singapore/toto/"
    "page/{page}/per-page/50/summary-view"
)
SOURCE_USER_AGENT = "Mozilla/5.0 (compatible; TotoAnalysisApp/1.0; educational)"

# --- CORS (Vue dev server) ---
CORS_ORIGINS = os.environ.get(
    "TOTO_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Persistent honesty disclaimer surfaced by the API and UI.
DISCLAIMER = (
    "Toto draws are independent random events. No method can predict future "
    "draws better than chance; the jackpot odds are 1 in 13,983,816 and the "
    "expected value of a ticket is negative."
)
