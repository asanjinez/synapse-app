import os
from litellm import completion, acompletion


def get_model() -> str:
    return os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-6")


def get_gateway_config() -> dict:
    return {
        "base_url": "https://ai-gateway.vercel.sh/v1",
        "api_key": os.getenv("VERCEL_AI_GATEWAY_KEY"),
    }


async def llm_call(messages: list, stream: bool = False):
    return await acompletion(
        model=get_model(),
        messages=messages,
        stream=stream,
        **get_gateway_config(),
    )
