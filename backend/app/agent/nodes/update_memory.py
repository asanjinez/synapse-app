"""update_memory node — persists profile, syncs mem0, triggers sleep agent. (ASA-25, ASA-31)"""
import asyncio
import logging
from datetime import datetime, timezone
from app.agent.state import SynapseState
from app.agent.checkpointer import get_store
from app.memory.mem0_client import add_memories

logger = logging.getLogger("synapse.update_memory")


async def update_memory(state: SynapseState) -> dict:
    profile = state.get("profile")
    if not profile:
        return {}

    user_id = state["user_id"]
    store = get_store()

    # Persist profile (remove ephemeral mem0_context before saving)
    profile_to_save = {k: v for k, v in profile.items() if k != "mem0_context"}
    await store.aput(
        namespace=(user_id, "profile"),
        key="data",
        value=profile_to_save,
    )

    messages = state.get("messages", [])
    if messages:
        asyncio.create_task(_run_background(user_id, messages))

    return {}


async def _run_background(user_id: str, messages: list) -> None:
    try:
        messages_dicts = []
        for m in messages:
            role = getattr(m, "type", "unknown")
            content = getattr(m, "content", "")
            if content:
                messages_dicts.append({"role": role, "content": content})

        # Save conversation to mem0 for semantic retrieval in future sessions
        await add_memories(user_id, messages_dicts)

        # Consolidate session in background
        from app.workers.sleep_agent import consolidate_session
        session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        await consolidate_session(user_id, session_id, messages_dicts)

    except Exception:
        logger.exception("background memory update failed for user=%s", user_id)
