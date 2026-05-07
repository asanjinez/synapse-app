"""mem0 semantic memory wrapper. (ASA-25)"""
import logging
from app.config import settings

logger = logging.getLogger("synapse.mem0")

_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.mem0_api_key:
            logger.warning("MEM0_API_KEY not set — mem0 disabled")
            return None
        try:
            from mem0 import AsyncMemoryClient
            _client = AsyncMemoryClient(api_key=settings.mem0_api_key)
        except ImportError:
            logger.warning("mem0ai not installed — mem0 disabled")
    return _client


async def search_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    client = _get_client()
    if client is None:
        return []
    try:
        results = await client.search(query, user_id=user_id, limit=limit)
        return [r["memory"] for r in results if "memory" in r]
    except Exception:
        logger.exception("mem0 search failed for user=%s", user_id)
        return []


async def add_memories(user_id: str, messages: list[dict]) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        await client.add(messages, user_id=user_id)
        logger.info("mem0 memories added for user=%s", user_id)
    except Exception:
        logger.exception("mem0 add failed for user=%s", user_id)
