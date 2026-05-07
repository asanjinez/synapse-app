import logging
from typing import Literal
from app.agent.state import SynapseState
from app.memory.fsrs import check_emergency_mode

logger = logging.getLogger("synapse.route")


def route_node(state: SynapseState) -> dict:
    profile = state.get("profile", {})

    if not profile.get("onboarding_complete"):
        return {"route": "onboarding", "emergency_mode": False}

    emergency = check_emergency_mode(profile.get("deadline"))

    last_messages = state.get("messages", [])
    wants_review = _user_wants_review(last_messages)
    destination = "review" if wants_review else "session"

    logger.info("route → %s | emergency=%s", destination, emergency)
    return {"route": destination, "emergency_mode": emergency}


def _user_wants_review(messages: list) -> bool:
    if not messages:
        return False
    last = messages[-1]
    content = getattr(last, "content", "") or ""
    keywords = ("repaso", "review", "revisar", "spaced repetition", "repasar")
    return any(k in content.lower() for k in keywords)


def get_route(state: SynapseState) -> Literal["onboarding", "session", "review"]:
    return state["route"]
