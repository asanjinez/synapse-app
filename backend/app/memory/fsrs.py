"""FSRS-6 spaced repetition logic. (ASA-23)"""
import logging
from datetime import datetime, timezone, date
from typing import Any

from fsrs import Scheduler, Card, Rating

logger = logging.getLogger("synapse.fsrs")

_scheduler = Scheduler()

_SCORE_TO_RATING = {
    0: Rating.Again,
    1: Rating.Again,
    2: Rating.Hard,
    3: Rating.Hard,
    4: Rating.Good,
    5: Rating.Easy,
}

EMERGENCY_THRESHOLD_DAYS = 14
EMERGENCY_MAX_INTERVAL_DAYS = 2


def check_emergency_mode(deadline: str | None) -> bool:
    if not deadline:
        return False
    try:
        deadline_date = date.fromisoformat(deadline)
        days_remaining = (deadline_date - date.today()).days
        return days_remaining <= EMERGENCY_THRESHOLD_DAYS
    except (ValueError, TypeError):
        return False


def _card_from_db(row: dict[str, Any]) -> Card:
    card = Card()
    card.stability = float(row["stability"])
    card.difficulty = float(row["difficulty"])
    return card


def compute_retrievability(card: Card) -> float:
    return _scheduler.get_card_retrievability(card)


async def update_mastery(user_id: str, node_id: str, score: int, pool) -> dict:
    """Apply FSRS-6 review and persist results. Returns updated item dict."""
    score = max(0, min(5, score))
    rating = _SCORE_TO_RATING[score]

    async with pool.connection() as conn:
        row = await (await conn.execute(
            """
            SELECT id, stability, difficulty, next_review_at
            FROM fsrs_items
            WHERE user_id = $1 AND node_id = $2
            LIMIT 1
            """,
            user_id, node_id,
        )).fetchone()

        if row is None:
            logger.warning("fsrs_item not found for node_id=%s — creating", node_id)
            await conn.execute(
                """
                INSERT INTO fsrs_items (user_id, node_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                user_id, node_id,
            )
            row = await (await conn.execute(
                "SELECT id, stability, difficulty, next_review_at FROM fsrs_items WHERE user_id=$1 AND node_id=$2",
                user_id, node_id,
            )).fetchone()

        card = _card_from_db(dict(row))
        updated_card, _ = _scheduler.review_card(card, rating)

        new_stability = updated_card.stability
        new_difficulty = updated_card.difficulty
        new_retrievability = compute_retrievability(updated_card)
        next_review = updated_card.due

        mastery_pct = min(100.0, new_retrievability * 100)

        await conn.execute(
            """
            UPDATE fsrs_items
            SET stability=$1, difficulty=$2, retrievability=$3,
                next_review_at=$4, status='pending'
            WHERE id=$5
            """,
            new_stability, new_difficulty, new_retrievability, next_review, row["id"],
        )
        await conn.execute(
            "UPDATE roadmap_nodes SET mastery_pct=$1 WHERE id=$2",
            mastery_pct, node_id,
        )

    logger.info(
        "mastery updated node=%s score=%s stability=%.2f next_review=%s",
        node_id, score, new_stability, next_review,
    )
    return {
        "node_id": node_id,
        "stability": new_stability,
        "difficulty": new_difficulty,
        "retrievability": new_retrievability,
        "next_review_at": next_review.isoformat(),
        "mastery_pct": mastery_pct,
    }


async def get_next_review_items(user_id: str, pool, emergency: bool = False) -> list[dict]:
    """Return overdue fsrs_items. In emergency mode, order by retrievability asc."""
    order = "retrievability ASC" if emergency else "next_review_at ASC"
    async with pool.connection() as conn:
        rows = await (await conn.execute(
            f"""
            SELECT fi.id, fi.node_id, fi.stability, fi.difficulty, fi.retrievability,
                   fi.next_review_at, rn.topic
            FROM fsrs_items fi
            JOIN roadmap_nodes rn ON fi.node_id = rn.id
            WHERE fi.user_id = $1
              AND fi.next_review_at <= NOW()
              AND fi.status = 'pending'
            ORDER BY {order}
            LIMIT 20
            """,
            user_id,
        )).fetchall()

    return [dict(r) for r in rows]


async def get_overdue_items(pool) -> list[dict]:
    """Return all overdue items across all users (for scheduler cron)."""
    async with pool.connection() as conn:
        rows = await (await conn.execute(
            """
            SELECT fi.id, fi.user_id, fi.node_id, fi.next_review_at, rn.topic
            FROM fsrs_items fi
            JOIN roadmap_nodes rn ON fi.node_id = rn.id
            WHERE fi.next_review_at <= NOW() AND fi.status = 'pending'
            ORDER BY fi.next_review_at ASC
            """,
        )).fetchall()
    return [dict(r) for r in rows]


async def mark_notified(item_id: str, pool) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE fsrs_items SET status='notified' WHERE id=$1", item_id
        )
