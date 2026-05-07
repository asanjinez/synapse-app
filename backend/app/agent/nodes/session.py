"""Session node — main learning session with tools and MCP guardrails. (ASA-27, ASA-28)"""
from langchain_core.messages import SystemMessage
from app.agent.state import SynapseState
from app.agent.llm import get_llm
from app.agent.tools import ALL_TOOLS

def _response_time_hint(ms: int) -> str:
    seconds = ms / 1000
    if seconds < 10:
        return (
            "El usuario respondió en menos de 10 segundos — señal de alta confianza. "
            "Si pide autoevaluación y da score ≥ 4, usá ese score sin ajuste."
        )
    elif seconds < 30:
        return (
            f"El usuario tardó {seconds:.0f} segundos en responder — confianza moderada. "
            "Usá el score autoevaluado sin ajuste."
        )
    else:
        return (
            f"El usuario tardó {seconds:.0f} segundos en responder — señal de dificultad. "
            "Si da score ≥ 4, bajalo en 1 al llamar update_mastery (ej: score=4 → pasalo como 3). "
            "Nunca menciones el tiempo al usuario."
        )


_SYSTEM_BASE = """\
Eres Synapse, un orquestador de conocimiento personal en una sesión de aprendizaje.

Reglas que NUNCA puedes romper:
- Nunca das la respuesta directa si el usuario falla — guía socráticamente con pistas.
- Nunca avanzas sobre un tema sin material sin avisarlo explícitamente.
- Nunca sales de las fuentes del usuario sin avisar.
- Si el deadline es menor a 14 días, informa al usuario y propone modo emergencia.

Herramientas disponibles y cuándo usarlas:
- `search_user_materials`: SIEMPRE antes de explicar un concepto — buscá en los PDFs del usuario.
- `get_roadmap`: para ver el plan de estudios y el progreso.
- `update_mastery`: después de evaluar la comprensión del usuario.
- `get_next_review_items`: si el usuario quiere ver qué tiene pendiente de repasar.
- `update_roadmap`: para ajustar el plan en tiempo real.
- `read_user_profile`: si necesitás contexto adicional sobre el usuario.

- `think_step_by_step`: antes de explicar un concepto difícil, diseñar un plan de estudio,
  o diagnosticar una brecha de conocimiento. No usar para respuestas simples.

Acceso a recursos externos (fetch):
- NUNCA busques fuera de las fuentes del usuario sin su permiso explícito.
- Si el tema no está cubierto, decí: "Esto no está en tu bibliografía.
  ¿Querés que busque información externa?" y esperá confirmación.
- Solo si el usuario acepta en este turno → podés hacer referencia a conocimiento externo.
"""


async def session_node(state: SynapseState) -> dict:
    llm = get_llm().bind_tools(ALL_TOOLS)
    profile = state.get("profile", {})

    context_lines = [_SYSTEM_BASE]
    if profile.get("goal"):
        context_lines.append(f"Objetivo del usuario: {profile['goal']}")
    if profile.get("deadline"):
        context_lines.append(f"Deadline: {profile['deadline']}")
    if profile.get("sources"):
        context_lines.append(f"Fuentes disponibles: {', '.join(profile['sources'])}")
    if profile.get("preferred_formats"):
        context_lines.append(
            f"Formatos que le funcionan al usuario: {', '.join(profile['preferred_formats'])}"
        )

    response_time_ms = state.get("response_time_ms")
    if response_time_ms is not None:
        context_lines.append(_response_time_hint(response_time_ms))

    messages = [SystemMessage(content="\n\n".join(context_lines))] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}
