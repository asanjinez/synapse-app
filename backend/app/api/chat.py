import asyncio
import logging
import os
from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import settings

logger = logging.getLogger("synapse.chat")
router = APIRouter()

_EXTRACT_TOPICS_PROMPT = """\
Analyze this academic document and extract a structured summary:
1. Main topic and subtopics (hierarchical)
2. Key concepts per subtopic (2-3 each)
3. Estimated difficulty level (beginner / intermediate / advanced)
4. Recommended study order

Be concise. Plain text, no JSON. Max 800 words.

Document (first 8000 words):
{text}
"""


class ChatRequest(BaseModel):
    messages: list[dict]
    user_id: str | None = None
    response_time_ms: int | None = None
    pdf_url: str | None = None


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


async def _extract_topics_summary(text: str) -> str:
    from app.agent.llm import get_llm
    llm = get_llm()
    words = text.split()[:8000]
    truncated = " ".join(words)
    response = await llm.ainvoke([
        SystemMessage(content="You are an expert at analyzing academic documents."),
        HumanMessage(content=_EXTRACT_TOPICS_PROMPT.format(text=truncated)),
    ])
    return getattr(response, "content", "") or ""


async def _process_pdf_from_blob(pdf_url: str, user_id: str) -> tuple[str, str]:
    """Download blob PDF, extract text, return (source_id, topics_summary)."""
    from app.memory.pdf import download_from_blob, extract_text_docling, chunk_text, create_source, update_source_status
    from app.memory.vector import save_chunks
    from app.agent.checkpointer import get_pool

    pool = get_pool()
    filename = pdf_url.split("/")[-1].split("?")[0]
    tmp_path = None

    try:
        tmp_path = await download_from_blob(pdf_url)
        text = extract_text_docling(tmp_path)

        if not text.strip():
            logger.warning("empty text from blob PDF | user_id=%s", user_id)
            return "", ""

        source_id = await create_source(user_id, filename, pool)
        logger.info("pdf_url detected | user_id=%s source_id=%s", user_id, source_id)

        # Background: chunk + embed for future RAG
        chunks = chunk_text(text)
        asyncio.create_task(_save_chunks_bg(source_id, chunks, pool))

        # Immediate: extract topics summary for agent
        summary = await _extract_topics_summary(text)
        logger.info("topics extracted | user_id=%s chars=%d", user_id, len(summary))

        await update_source_status(source_id, "processed", pool)
        return source_id, summary

    except Exception:
        logger.exception("pdf processing failed | user_id=%s url=%s", user_id, pdf_url)
        return "", ""
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


async def _save_chunks_bg(source_id: str, chunks: list[str], pool) -> None:
    from app.memory.vector import save_chunks
    try:
        await save_chunks(source_id, chunks, pool)
    except Exception:
        logger.exception("background chunk save failed | source_id=%s", source_id)


@router.post("/api/chat")
async def chat(
    request: ChatRequest,
    x_user_id: str | None = Header(None),
):
    user_id = request.user_id or x_user_id or "demo-user"
    if request.messages:
        last_msg = request.messages[-1]
        last_content = last_msg.get("content") or ""
        attachments = last_msg.get("experimental_attachments") or []
        files_info = [f"{a.get('name', '?')} ({a.get('contentType', '?')})" for a in attachments] if attachments else []
        logger.info(
            "chat request | user_id=%s messages=%d\n  message: %s%s%s",
            user_id, len(request.messages),
            last_content,
            f"\n  files: {', '.join(files_info)}" if files_info else "",
            f"\n  pdf_url: {request.pdf_url}" if request.pdf_url else "",
        )
    else:
        logger.info("chat request | user_id=%s messages=0", user_id)

    try:
        from app.agent.graph import get_graph
        graph = get_graph()
    except Exception as exc:
        logger.exception("failed to load graph: %s", exc)
        async def error_stream():
            yield f"data: [ERROR] failed to load graph: {exc}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # Process PDF if attached
    new_material: str | None = None
    if request.pdf_url and settings.blob_read_write_token:
        _, new_material = await _process_pdf_from_blob(request.pdf_url, user_id)
        new_material = new_material or None

    lc_messages = _to_lc_messages(request.messages[-1:])
    config = {"configurable": {"thread_id": user_id}}

    async def generate():
        yield ": connected\n\n"
        token_count = 0
        try:
            logger.info("starting graph stream | user_id=%s", user_id)
            async for event in graph.astream_events(
                {
                    "messages": lc_messages,
                    "user_id": user_id,
                    "response_time_ms": request.response_time_ms,
                    "new_material": new_material,
                },
                config=config,
                version="v2",
            ):
                kind = event["event"]
                if kind == "on_chain_start":
                    logger.debug("node start | name=%s", event.get("name"))
                elif kind == "on_chain_end":
                    logger.debug("node end   | name=%s", event.get("name"))
                elif kind == "on_tool_start":
                    logger.info("tool call | name=%s args=%s", event.get("name"), str(event.get("data", {}).get("input", ""))[:200])
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
