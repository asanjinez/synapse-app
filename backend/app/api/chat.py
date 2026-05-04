import logging
import os
import traceback

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

# [v0] Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
    # [v0] Debug: Log environment and request info
    logger.info("[v0] ===== CHAT ENDPOINT CALLED =====")
    logger.info(f"[v0] Request user_id: {request.user_id}")
    logger.info(f"[v0] Header x_user_id: {x_user_id}")
    logger.info(f"[v0] Messages count: {len(request.messages)}")
    logger.info(f"[v0] Messages: {request.messages}")
    
    # [v0] Debug: Check environment variables
    logger.info("[v0] Checking environment variables...")
    env_vars = {
        "DATABASE_URL": "set" if os.getenv("DATABASE_URL") else "NOT SET",
        "VERCEL_AI_GATEWAY_KEY": "set" if os.getenv("VERCEL_AI_GATEWAY_KEY") else "NOT SET",
        "MODEL_NAME": os.getenv("MODEL_NAME", "NOT SET"),
        "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL", "NOT SET"),
    }
    logger.info(f"[v0] Environment check: {env_vars}")

    try:
        from app.agent.graph import get_graph
        logger.info("[v0] Successfully imported get_graph")
    except Exception as e:
        logger.error(f"[v0] Failed to import get_graph: {e}")
        logger.error(f"[v0] Traceback: {traceback.format_exc()}")
        raise

    user_id = request.user_id or x_user_id or "demo-user"
    logger.info(f"[v0] Using user_id: {user_id}")
    
    try:
        lc_messages = _to_lc_messages(request.messages)
        logger.info(f"[v0] Converted to {len(lc_messages)} LangChain messages")
    except Exception as e:
        logger.error(f"[v0] Failed to convert messages: {e}")
        logger.error(f"[v0] Traceback: {traceback.format_exc()}")
        raise

    try:
        graph = get_graph()
        logger.info("[v0] Successfully got graph")
    except Exception as e:
        logger.error(f"[v0] Failed to get graph: {e}")
        logger.error(f"[v0] Traceback: {traceback.format_exc()}")
        raise

    config = {"configurable": {"thread_id": user_id}}

    async def generate():
        logger.info("[v0] Starting stream generation...")
        try:
            async for event in graph.astream_events(
                {"messages": lc_messages, "user_id": user_id},
                config=config,
                version="v2",
            ):
                logger.debug(f"[v0] Event type: {event['event']}")
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    token: str = getattr(chunk, "content", "") or ""
                    if token:
                        logger.debug(f"[v0] Streaming token: {token[:50]}...")
                        # SSE lines cannot contain bare newlines — encode them
                        yield f"data: {token.replace(chr(10), '\\n')}\n\n"
            logger.info("[v0] Stream completed successfully")
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error(f"[v0] Stream error: {exc}")
            logger.error(f"[v0] Traceback: {traceback.format_exc()}")
            yield f"data: [ERROR] {exc}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
