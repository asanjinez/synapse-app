"""Agent tools — patrón Karpathy: el agente decide activamente qué cargar. (ASA-24)"""
import logging
from langchain_core.tools import tool

from app.agent.checkpointer import get_store, get_pool
from app.memory.fsrs import update_mastery as _update_mastery, get_next_review_items as _get_review_items
from app.memory.vector import search_user_materials as _search_materials

logger = logging.getLogger("synapse.tools")


@tool
async def read_user_profile(user_id: str) -> dict:
    """Load the user's profile from persistent store (goals, deadline, learning style)."""
    store = get_store()
    item = await store.aget(namespace=(user_id, "profile"), key="data")
    return item.value if item else {}


@tool
async def get_roadmap(user_id: str) -> list[dict]:
    """Return the user's active roadmap nodes with their status and mastery."""
    pool = get_pool()
    async with pool.connection() as conn:
        rows = await (await conn.execute(
            """
            SELECT id, topic, parent_id, status, target_date, mastery_pct
            FROM roadmap_nodes
            WHERE user_id = %s
            ORDER BY target_date ASC NULLS LAST
            """,
            (user_id,),
        )).fetchall()
    return [dict(r) for r in rows]


@tool
async def update_mastery(user_id: str, node_id: str, score: int) -> dict:
    """Update mastery and recalculate FSRS-6 schedule for a roadmap node.

    score: 0 (complete blank) to 5 (perfect recall)
    """
    pool = get_pool()
    return await _update_mastery(user_id, node_id, score, pool)


@tool
async def get_next_review_items(user_id: str) -> list[dict]:
    """Return overdue FSRS review items for today."""
    pool = get_pool()
    return await _get_review_items(user_id, pool)


@tool
async def search_user_materials(user_id: str, query: str) -> list[str]:
    """Semantic search over the user's uploaded PDFs and materials via pgvector.

    Returns up to 5 relevant text chunks. Never returns material from other users.
    """
    pool = get_pool()
    return await _search_materials(user_id, query, pool, limit=5)


@tool
async def update_roadmap(user_id: str, changes: dict) -> str:
    """Modify roadmap nodes: add, complete, or reprioritize.

    changes format:
      {"action": "complete", "node_id": "..."}
      {"action": "add", "topic": "...", "parent_id": null, "target_date": "YYYY-MM-DD"}
      {"action": "reprioritize", "node_id": "...", "target_date": "YYYY-MM-DD"}
    """
    pool = get_pool()
    action = changes.get("action")

    async with pool.connection() as conn:
        if action == "complete":
            await conn.execute(
                "UPDATE roadmap_nodes SET status='completed' WHERE id=%s AND user_id=%s",
                (changes["node_id"], user_id),
            )
        elif action == "add":
            await conn.execute(
                """
                INSERT INTO roadmap_nodes (user_id, topic, parent_id, target_date)
                VALUES (%s, %s, %s, %s::date)
                """,
                (user_id, changes.get("topic"), changes.get("parent_id"), changes.get("target_date")),
            )
        elif action == "reprioritize":
            await conn.execute(
                "UPDATE roadmap_nodes SET target_date=%s::date WHERE id=%s AND user_id=%s",
                (changes.get("target_date"), changes["node_id"], user_id),
            )
        else:
            return f"Unknown action: {action}"

    logger.info("roadmap updated user=%s action=%s", user_id, action)
    return f"Roadmap updated: {action}"


ALL_TOOLS = [
    read_user_profile,
    get_roadmap,
    update_mastery,
    get_next_review_items,
    search_user_materials,
    update_roadmap,
]
