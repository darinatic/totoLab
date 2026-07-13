"""Draw-day-aligned scheduled refresh.

Singapore Toto draws happen Monday and Thursday (~18:30 SGT). We fetch a few
hours later, twice a week - polite, low-frequency, and idempotent. The fetch
targets a community aggregator, not Singapore Pools directly.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import deps, ingest

log = logging.getLogger("toto.scheduler")
_scheduler: BackgroundScheduler | None = None


def _refresh_job() -> None:
    try:
        written = ingest.refresh(pages=(1, 2))
        deps.invalidate_cache()
        log.info("Scheduled refresh complete: %s draws upserted", written)
    except Exception:  # never let a fetch error kill the scheduler thread
        log.exception("Scheduled refresh failed")


def start() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = BackgroundScheduler(timezone="Asia/Singapore")
    # Mondays and Thursdays at 21:30 SGT, a few hours after the draw.
    sched.add_job(
        _refresh_job,
        CronTrigger(day_of_week="mon,thu", hour=21, minute=30),
        id="toto_refresh",
        replace_existing=True,
    )
    sched.start()
    _scheduler = sched
    log.info("Scheduler started (Mon/Thu 21:30 SGT)")
    return sched


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
