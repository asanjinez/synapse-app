from langgraph.graph import StateGraph, END
from app.agent.state import SynapseState
from app.agent.nodes.load_context import load_context
from app.agent.nodes.route import route_node, get_route
from app.agent.nodes.onboarding import onboarding_node
from app.agent.nodes.session import session_node
from app.agent.nodes.update_memory import update_memory
from app.agent.checkpointer import get_checkpointer, get_store

_compiled = None


def build_graph():
    g = StateGraph(SynapseState)

    g.add_node("load_context", load_context)
    g.add_node("route", route_node)
    g.add_node("onboarding", onboarding_node)
    g.add_node("session", session_node)
    g.add_node("update_memory", update_memory)

    g.set_entry_point("load_context")
    g.add_edge("load_context", "route")
    g.add_conditional_edges("route", get_route, {
        "onboarding": "onboarding",
        "session": "session",
    })
    g.add_edge("onboarding", "update_memory")
    g.add_edge("session", "update_memory")
    g.add_edge("update_memory", END)

    return g.compile(
        checkpointer=get_checkpointer(),
        store=get_store(),
    )


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
