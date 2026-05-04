from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Phase 2+
    database_url: Optional[str] = None
    vercel_ai_gateway_key: Optional[str] = None
    # LLM
    model_name: str = "anthropic/claude-sonnet-4-6"
    embedding_model: str = "text-embedding-3-small"
    # Observability (Phase 2+)
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "false"
    langchain_project: str = "synapse"
    # Mem0 (Phase 3)
    mem0_api_key: str = ""
    # CORS
    frontend_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
