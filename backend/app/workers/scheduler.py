"""APScheduler — hourly cron for FSRS-6 overdue review detection. (ASA-30)"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.agent.checkpointer import get_pool
from app.memory.fsrs import get_overdue_items, mark_notified

logger = logging.getLogger("synapse.scheduler")

scheduler = AsyncIOScheduler()


async def check_pending_reviews() -> None:
    pool = get_pool()
    try:
        items = await get_overdue_items(pool)
        if not items:
            return

        logger.info("found %d overdue review items", len(items))
        for item in items:
            await _notify_user(item)
            await mark_notified(item["id"], pool)
    except Exception:
        logger.exception("scheduler check_pending_reviews failed")


async def _notify_user(item: dict) -> None:
    # Stub: log only. Phase 4+ will add Discord/Telegram/email.
    logger.info(
        "[REVIEW DUE] user=%s topic=%s due=%s",
        item["user_id"],
        item.get("topic", "unknown"),
        item.get("next_review_at"),
    )


def start_scheduler() -> None:
    scheduler.add_job(check_pending_reviews, "interval", hours=1, id="fsrs_cron")
    scheduler.start()
    logger.info("APScheduler started — FSRS cron every 1h")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")
