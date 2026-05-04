from typing import Literal
from app.agent.state import SynapseState


def route_node(state: SynapseState) -> dict:
    profile = state.get("profile", {})
    destination = "session" if profile.get("onboarding_complete") else "onboarding"
    return {"route": destination}


def get_route(state: SynapseState) -> Literal["onboarding", "session"]:
    return state["route"]
