from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()


class ChatRequest(BaseModel):
    messages: list[dict]
    user_id: str | None = None


def _to_lc_messages(messages: list[dict]) -> list:
    result = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if not content:
            for part in m.get("parts", []):
                if isinstance(part, dict) and part.get("type") == "text":
                    content = part.get("text", "")
                    break
        if not content:
            continue
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
    return result


@router.post("/api/chat")
async def chat(
    request: ChatRequest,
    x_user_id: str | None = Header(None),
):
    from app.agent.graph import get_graph

    user_id = request.user_id or x_user_id or "demo-user"
    lc_messages = _to_lc_messages(request.messages)
    graph = get_graph()
    config = {"configurable": {"thread_id": user_id}}

    async def generate():
        try:
            async for event in graph.astream_events(
                {"messages": lc_messages, "user_id": user_id},
                config=config,
                version="v2",
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    token: str = getattr(chunk, "content", "") or ""
                    if token:
                        # SSE lines cannot contain bare newlines — encode them
                        yield f"data: {token.replace(chr(10), '\\n')}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
