"""Draw-day-aligned scheduled refresh.

Singapore Toto draws happen Monday and Thursday (~18:30 SGT). We fetch a few
hours later, twice a week - polite, low-frequency, and idempotent. The fetch
targets a community aggregator, not Singapore Pools directly.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import deps, fourd_ingest, ingest

log = logging.getLogger("toto.scheduler")
_scheduler: BackgroundScheduler | None = None


def _refresh_job() -> None:
    try:
        written = ingest.refresh(pages=(1, 2))
        deps.invalidate_cache()
        log.info("Toto refresh complete: %s draws upserted", written)
    except Exception:  # never let a fetch error kill the scheduler thread
        log.exception("Toto refresh failed")


def _fourd_refresh_job() -> None:
    try:
        written = fourd_ingest.refresh(limit=3)
        deps.invalidate_cache()
        log.info("4D refresh complete: %s rows upserted", written)
    except Exception:
        log.exception("4D refresh failed")


def start() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = BackgroundScheduler(timezone="Asia/Singapore")
    # Toto draws Mon/Thu; 4D draws Wed/Sat/Sun. Fetch a few hours after each.
    sched.add_job(_refresh_job, CronTrigger(day_of_week="mon,thu", hour=21, minute=30),
                  id="toto_refresh", replace_existing=True)
    sched.add_job(_fourd_refresh_job, CronTrigger(day_of_week="wed,sat,sun", hour=21, minute=30),
                  id="fourd_refresh", replace_existing=True)
    sched.start()
    _scheduler = sched
    log.info("Scheduler started (Toto Mon/Thu, 4D Wed/Sat/Sun, 21:30 SGT)")
    return sched


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
