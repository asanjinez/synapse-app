"""Sleep-time agent — post-session memory consolidation in background. (ASA-31)"""
import logging
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.checkpointer import get_store, get_pool
from app.agent.llm import get_llm

logger = logging.getLogger("synapse.sleep_agent")

_CONSOLIDATION_PROMPT = """\
Eres un analizador de sesiones de aprendizaje. Dada la conversación a continuación,
genera un resumen estructurado en JSON con estos campos:
- key_concepts: list[str] — conceptos clave trabajados
- successful_formats: list[str] — formatos que funcionaron (analogía, Feynman, ejercicio, etc.)
- weak_areas: list[str] — áreas donde el usuario mostró dificultad
- insights: str — observaciones sobre el estilo de aprendizaje del usuario

Responde SOLO con el JSON, sin texto adicional.
"""


async def consolidate_session(user_id: str, session_id: str, messages: list[dict]) -> None:
    """Summarize a session and persist notes to PostgresStore. Non-blocking."""
    try:
        llm = get_llm()
        conversation_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages
            if m.get("content")
        )

        response = await llm.ainvoke([
            SystemMessage(content=_CONSOLIDATION_PROMPT),
            HumanMessage(content=f"Conversación:\n{conversation_text}"),
        ])

        notes_raw = response.content if hasattr(response, "content") else str(response)

        store = get_store()
        await store.aput(
            namespace=(user_id, "memories"),
            key=f"session_{session_id}",
            value={"raw": notes_raw, "session_id": session_id},
        )
        logger.info("session consolidated user=%s session=%s", user_id, session_id)

        await _detect_learning_patterns(user_id, notes_raw, store)

    except Exception:
        logger.exception("consolidate_session failed user=%s session=%s", user_id, session_id)


async def _detect_learning_patterns(user_id: str, notes_raw: str, store) -> None:
    try:
        import json
        notes = json.loads(notes_raw)

        profile_item = await store.aget(namespace=(user_id, "profile"), key="data")
        profile = profile_item.value if profile_item else {}

        if notes.get("successful_formats"):
            existing = profile.get("preferred_formats", [])
            merged = list(set(existing + notes["successful_formats"]))
            profile["preferred_formats"] = merged
            await store.aput(namespace=(user_id, "profile"), key="data", value=profile)
            logger.debug("learning patterns updated user=%s formats=%s", user_id, merged)
    except Exception:
        logger.debug("_detect_learning_patterns skipped (non-JSON notes or error)")
