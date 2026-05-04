import logging
import os

from langchain_litellm import ChatLiteLLM

# [v0] Configure logging
logger = logging.getLogger(__name__)


def get_llm() -> ChatLiteLLM:
    model = os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-6")
    api_key = os.getenv("VERCEL_AI_GATEWAY_KEY", "")
    
    logger.info("[v0] ===== GET LLM CALLED =====")
    logger.info(f"[v0] Model: {model}")
    logger.info(f"[v0] API Key exists: {bool(api_key)}")
    logger.info(f"[v0] API Key length: {len(api_key) if api_key else 0}")
    
    if not api_key:
        logger.warning("[v0] VERCEL_AI_GATEWAY_KEY is not set!")
    
    return ChatLiteLLM(
        model=model,
        api_base="https://ai-gateway.vercel.sh/v1",
        api_key=api_key,
        streaming=True,
    )
