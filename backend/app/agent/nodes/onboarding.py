from langchain_core.messages import SystemMessage
from app.agent.state import SynapseState
from app.agent.llm import get_llm

_SYSTEM = """\
Eres Synapse, un orquestador de conocimiento personal.

En este primer encuentro, tu misión es descubrir tres cosas:
1. Qué quiere aprender el usuario (objetivo concreto)
2. Si tiene deadline
3. Qué materiales tiene disponibles (PDFs, libros, links)

Guías de conversación:
- Una sola pregunta por turno. Sé conversacional, no hagas listas.
- No preguntes cómo aprende el usuario — lo observarás en las sesiones.
- Cuando tengas objetivo + al menos una fuente o deadline, termina con la señal ONBOARDING_COMPLETE
  en la última línea (el usuario NO la verá — es interna).

Ejemplo de cierre:
"¡Perfecto! Ya tengo todo lo que necesito para armar tu plan. Empezamos cuando quieras."
ONBOARDING_COMPLETE
"""


async def onboarding_node(state: SynapseState) -> dict:
    llm = get_llm()
    messages = [SystemMessage(content=_SYSTEM)] + state["messages"]
    response = await llm.ainvoke(messages)

    content: str = response.content or ""
    updates: dict = {}

    if "ONBOARDING_COMPLETE" in content:
        content = content.replace("ONBOARDING_COMPLETE", "").strip()
        response.content = content
        profile = dict(state.get("profile", {}))
        profile["onboarding_complete"] = True
        updates["profile"] = profile

    updates["messages"] = [response]
    return updates
