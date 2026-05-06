from app.agent.state import SynapseState
from app.agent.checkpointer import get_store


async def update_memory(state: SynapseState) -> dict:
    profile = state.get("profile")
    if not profile:
        return {}
    store = get_store()
    await store.aput(
        namespace=(state["user_id"], "profile"),
        key="data",
        value=profile,
    )
    return {}
