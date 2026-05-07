from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.agent.state import SynapseState
from app.agent.nodes.load_context import load_context
from app.agent.nodes.route import route_node, get_route
from app.agent.nodes.onboarding import onboarding_node
from app.agent.nodes.session import session_node
from app.agent.nodes.review import review_node
from app.agent.nodes.update_memory import update_memory
from app.agent.checkpointer import get_checkpointer, get_store
from app.agent.tools import ALL_TOOLS

_compiled = None


def _should_use_tools(state: SynapseState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "update_memory"
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "update_memory"


def build_graph():
    g = StateGraph(SynapseState)
    tool_node = ToolNode(ALL_TOOLS)

    g.add_node("load_context", load_context)
    g.add_node("route", route_node)
    g.add_node("onboarding", onboarding_node)
    g.add_node("session", session_node)
    g.add_node("review", review_node)
    g.add_node("tools", tool_node)
    g.add_node("update_memory", update_memory)

    g.set_entry_point("load_context")
    g.add_edge("load_context", "route")

    g.add_conditional_edges("route", get_route, {
        "onboarding": "onboarding",
        "session": "session",
        "review": "review",
    })

    # Tool loop for session and review
    g.add_conditional_edges("session", _should_use_tools, {
        "tools": "tools",
        "update_memory": "update_memory",
    })
    g.add_conditional_edges("review", _should_use_tools, {
        "tools": "tools",
        "update_memory": "update_memory",
    })
    # After tool execution, return to whichever node originated the call
    g.add_conditional_edges("tools", _route_after_tools, {
        "session": "session",
        "review": "review",
    })

    g.add_edge("onboarding", "update_memory")
    g.add_edge("update_memory", END)

    return g.compile(
        checkpointer=get_checkpointer(),
        store=get_store(),
    )


def _route_after_tools(state: SynapseState) -> str:
    return state.get("route", "session")


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
