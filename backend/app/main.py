"""FastAPI application entrypoint.

Serves the JSON API under `/api/*` and, in production, the built Vue SPA at `/`
from the same origin (so a single container hosts both). In local dev the SPA is
served by Vite instead and this app just exposes the API.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, deps, fourd_db, fourd_ingest, ingest, scheduler
from .routers import draws, insights, stats
from .routers import fourd_draws, fourd_insights, fourd_stats

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("toto")

# Built frontend, if present (populated in the production image).
STATIC_DIR = Path(os.environ.get("TOTO_STATIC_DIR", config.BASE_DIR.parent / "frontend" / "dist"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    seeded = ingest.seed_if_empty()
    if seeded:
        log.info("Seeded %s Toto draws from bundled CSV", seeded)
    fourd_db.init_db()
    seeded_4d = fourd_ingest.seed_if_empty()
    if seeded_4d:
        log.info("Seeded %s 4D rows from bundled CSV", seeded_4d)
    deps.invalidate_cache()
    # In-process scheduler is for always-on/local use. In production we refresh
    # data via a GitHub Actions cron that commits the seed CSV (see README).
    if os.environ.get("TOTO_DISABLE_SCHEDULER") != "1":
        scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Singapore Toto Analysis API",
    description=(
        "Honest statistical analysis of Singapore Toto. Generates picks for fun "
        "and proves - via backtesting - that no strategy beats random. " + config.DISCLAIMER
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- JSON API (all under /api) ---
app.include_router(draws.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(insights.router, prefix="/api")

app.include_router(fourd_draws.router, prefix="/api/4d")
app.include_router(fourd_stats.router, prefix="/api/4d")
app.include_router(fourd_insights.router, prefix="/api/4d")


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "toto_draws": db.count_draws(),
            "fourd_draws": fourd_db.count_draws()}


@app.post("/api/admin/refresh", tags=["meta"])
def admin_refresh(pages: int = 2):
    written = ingest.refresh(pages=tuple(range(1, pages + 1)))
    written_4d = fourd_ingest.refresh(limit=3)
    deps.invalidate_cache()
    return {"toto_upserted": written, "fourd_upserted": written_4d,
            "toto_total": db.count_draws(), "fourd_total": fourd_db.count_draws()}


# --- SPA (production single-container) ---
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", tags=["spa"])
    def serve_spa(full_path: str):
        """Serve real static files, else fall back to index.html for SPA routing."""
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/", tags=["meta"])
    def root():
        return {"name": "Singapore Toto Analysis API", "docs": "/docs",
                "api": "/api", "disclaimer": config.DISCLAIMER}
