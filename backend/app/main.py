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

from . import config, db, deps, ingest, scheduler
from .routers import draws, insights, stats

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("toto")

# Built frontend, if present (populated in the production image).
STATIC_DIR = Path(os.environ.get("TOTO_STATIC_DIR", config.BASE_DIR.parent / "frontend" / "dist"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    seeded = ingest.seed_if_empty()
    if seeded:
        log.info("Seeded %s draws from bundled CSV", seeded)
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


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "draws": db.count_draws()}


@app.post("/api/admin/refresh", tags=["meta"])
def admin_refresh(pages: int = 2):
    written = ingest.refresh(pages=tuple(range(1, pages + 1)))
    deps.invalidate_cache()
    return {"upserted": written, "total": db.count_draws()}


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
