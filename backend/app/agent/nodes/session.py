from langchain_core.messages import SystemMessage
from app.agent.state import SynapseState
from app.agent.llm import get_llm

_SYSTEM_BASE = """\
Eres Synapse, un orquestador de conocimiento personal en una sesión de aprendizaje.

Reglas que NUNCA puedes romper:
- Nunca das la respuesta directa si el usuario falla — guía socráticamente con pistas.
- Nunca avanzas sobre un tema sin material sin avisarlo explícitamente.
- Nunca sales de las fuentes del usuario sin avisar.
- Si el deadline es menor a 14 días, activa modo de emergencia: active recall intensivo,
  intervalos cortos, avísale al usuario que cambiás de modo.

Tu objetivo: validar comprensión real, no memorización. Adaptá el formato según señales
de retención del usuario.
"""


async def session_node(state: SynapseState) -> dict:
    llm = get_llm()
    profile = state.get("profile", {})

    context_lines = [_SYSTEM_BASE]
    if profile.get("goal"):
        context_lines.append(f"Objetivo del usuario: {profile['goal']}")
    if profile.get("deadline"):
        context_lines.append(f"Deadline: {profile['deadline']}")
    if profile.get("sources"):
        context_lines.append(f"Fuentes disponibles: {', '.join(profile['sources'])}")

    messages = [SystemMessage(content="\n".join(context_lines))] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}
