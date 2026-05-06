import os
from langchain_litellm import ChatLiteLLM


def get_llm() -> ChatLiteLLM:
    return ChatLiteLLM(
        model=os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-6"),
        api_base="https://ai-gateway.vercel.sh/v1",
        api_key=os.getenv("VERCEL_AI_GATEWAY_KEY", ""),
        streaming=True,
    )
