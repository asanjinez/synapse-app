from app.agent.state import SynapseState, UserProfile
from app.agent.checkpointer import get_store

_DEFAULT_PROFILE: UserProfile = {
    "onboarding_complete": False,
    "goal": None,
    "deadline": None,
    "learning_style": None,
    "sources": [],
}


async def load_context(state: SynapseState) -> dict:
    store = get_store()
    item = await store.aget(namespace=(state["user_id"], "profile"), key="data")
    profile = item.value if item else dict(_DEFAULT_PROFILE)
    return {"profile": profile}
