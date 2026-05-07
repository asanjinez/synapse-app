"""Review node — active recall sessions scheduled by FSRS-6. (ASA-32)"""
from langchain_core.messages import SystemMessage
from app.agent.nodes.session import _response_time_hint
from app.agent.state import SynapseState
from app.agent.llm import get_llm
from app.agent.tools import ALL_TOOLS

_SYSTEM_NORMAL = """\
Eres Synapse en modo REPASO. Conduces sesiones de active recall puro — sin material nuevo.

Protocolo obligatorio:
1. Preguntá al usuario sobre el concepto a repasar — nunca des la respuesta directamente.
2. Escuchá la respuesta del usuario.
3. Evaluá sin revelar la respuesta correcta: usá la mayéutica socrática.
4. Pedile al usuario que se autoevalúe: "¿Cómo calificarías tu respuesta de 0 a 5?"
5. Invocá la tool `update_mastery` con el score recibido.
6. Al terminar todos los ítems: informá cuántos repasaste y el estado general.

Reglas inviolables:
- Nunca des la respuesta directa si el usuario falla.
- Nunca uses información fuera de los materiales del usuario sin avisar.
"""

_SYSTEM_EMERGENCY = """\
Eres Synapse en modo EMERGENCIA. El deadline es inminente.

Protocolo de emergencia:
- Priorizá los conceptos con retrievability más baja (más frágiles primero).
- Intervalos máximos de 1-2 días entre repasos.
- Más preguntas por sesión, menos explicación, active recall puro.
- Usá `get_next_review_items` para ver los ítems pendientes.
- Aplicá `update_mastery` después de cada evaluación.

Informale al usuario el número de ítems críticos y el tiempo disponible.
"""


async def review_node(state: SynapseState) -> dict:
    llm = get_llm().bind_tools(ALL_TOOLS)
    emergency = state.get("emergency_mode", False)
    profile = state.get("profile", {})

    system_prompt = _SYSTEM_EMERGENCY if emergency else _SYSTEM_NORMAL
    context_parts = [system_prompt]

    if profile.get("goal"):
        context_parts.append(f"Objetivo del usuario: {profile['goal']}")
    if profile.get("deadline"):
        context_parts.append(f"Deadline: {profile['deadline']}")
    if emergency:
        context_parts.append("MODO EMERGENCIA ACTIVO — priorizá por fragilidad.")

    response_time_ms = state.get("response_time_ms")
    if response_time_ms is not None:
        context_parts.append(_response_time_hint(response_time_ms))

    messages = [SystemMessage(content="\n\n".join(context_parts))] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}
