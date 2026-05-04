import logging
import traceback

from langgraph.graph import StateGraph, END
from app.agent.state import SynapseState
from app.agent.nodes.load_context import load_context
from app.agent.nodes.route import route_node, get_route
from app.agent.nodes.onboarding import onboarding_node
from app.agent.nodes.session import session_node
from app.agent.nodes.update_memory import update_memory
from app.agent.checkpointer import get_checkpointer, get_store

# [v0] Configure logging
logger = logging.getLogger(__name__)

_compiled = None


def build_graph():
    logger.info("[v0] ===== BUILD GRAPH CALLED =====")
    
    try:
        g = StateGraph(SynapseState)
        logger.info("[v0] StateGraph created")

        g.add_node("load_context", load_context)
        g.add_node("route", route_node)
        g.add_node("onboarding", onboarding_node)
        g.add_node("session", session_node)
        g.add_node("update_memory", update_memory)
        logger.info("[v0] All nodes added")

        g.set_entry_point("load_context")
        g.add_edge("load_context", "route")
        g.add_conditional_edges("route", get_route, {
            "onboarding": "onboarding",
            "session": "session",
        })
        g.add_edge("onboarding", "update_memory")
        g.add_edge("session", "update_memory")
        g.add_edge("update_memory", END)
        logger.info("[v0] All edges configured")

        logger.info("[v0] Getting checkpointer...")
        checkpointer = get_checkpointer()
        logger.info("[v0] Got checkpointer")
        
        logger.info("[v0] Getting store...")
        store = get_store()
        logger.info("[v0] Got store")

        logger.info("[v0] Compiling graph...")
        compiled = g.compile(
            checkpointer=checkpointer,
            store=store,
        )
        logger.info("[v0] ===== GRAPH BUILD COMPLETE =====")
        return compiled
    except Exception as e:
        logger.error(f"[v0] Failed to build graph: {e}")
        logger.error(f"[v0] Traceback: {traceback.format_exc()}")
        raise


def get_graph():
    global _compiled
    logger.info(f"[v0] get_graph called, _compiled is {'set' if _compiled else 'None'}")
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
