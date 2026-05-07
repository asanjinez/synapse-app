"""load_context node — loads profile and mem0 semantic memories. (ASA-25)"""
from app.agent.state import SynapseState, UserProfile
from app.agent.checkpointer import get_store
from app.memory.mem0_client import search_memories

_DEFAULT_PROFILE: UserProfile = {
    "onboarding_complete": False,
    "goal": None,
    "deadline": None,
    "learning_style": None,
    "sources": [],
}


async def load_context(state: SynapseState) -> dict:
    store = get_store()
    user_id = state["user_id"]

    item = await store.aget(namespace=(user_id, "profile"), key="data")
    profile = item.value if item else dict(_DEFAULT_PROFILE)

    # Load semantic memories from mem0 relevant to the current conversation
    last_message = ""
    if state.get("messages"):
        last = state["messages"][-1]
        last_message = getattr(last, "content", "") or ""

    if last_message:
        facts = await search_memories(user_id, last_message, limit=3)
        if facts:
            profile["mem0_context"] = facts

    return {"profile": profile}
