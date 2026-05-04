from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    messages: list[dict]
    user_id: str


@router.post("/api/chat")
async def chat(request: ChatRequest):
    # Phase 2: conectar LangGraph aquí
    async def generate():
        yield "data: Synapse online\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
