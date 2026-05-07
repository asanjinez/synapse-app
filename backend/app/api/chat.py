import logging
from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger("synapse.chat")
router = APIRouter()


class ChatRequest(BaseModel):
    messages: list[dict]
    user_id: str | None = None
    response_time_ms: int | None = None


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
    user_id = request.user_id or x_user_id or "demo-user"
    logger.info("chat request | user_id=%s messages=%d", user_id, len(request.messages))

    try:
        from app.agent.graph import get_graph
        graph = get_graph()
        logger.info("graph loaded | user_id=%s", user_id)
    except Exception as exc:
        logger.exception("failed to load graph: %s", exc)
        async def error_stream():
            yield f"data: [ERROR] failed to load graph: {exc}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    lc_messages = _to_lc_messages(request.messages)
    config = {"configurable": {"thread_id": user_id}}

    async def generate():
        yield ": connected\n\n"
        token_count = 0
        try:
            logger.info("starting graph stream | user_id=%s", user_id)
            async for event in graph.astream_events(
                {"messages": lc_messages, "user_id": user_id, "response_time_ms": request.response_time_ms},
                config=config,
                version="v2",
            ):
                kind = event["event"]
                if kind == "on_chain_start":
                    logger.debug("node start | name=%s", event.get("name"))
                elif kind == "on_chain_end":
                    logger.debug("node end   | name=%s", event.get("name"))
                elif kind == "on_chat_model_start":
                    logger.info("llm call start | node=%s", event.get("name"))
                elif kind == "on_chat_model_end":
                    logger.info("llm call end   | node=%s tokens=%d", event.get("name"), token_count)
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    token: str = getattr(chunk, "content", "") or ""
                    if token:
                        token_count += 1
                        yield f"data: {token.replace(chr(10), chr(92) + 'n')}\n\n"

            logger.info("stream complete | user_id=%s total_tokens=%d", user_id, token_count)
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("stream error | user_id=%s error=%s", user_id, exc)
            yield f"data: [ERROR] {exc}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
