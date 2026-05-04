from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    vercel_ai_gateway_key: str
    model_name: str = "anthropic/claude-sonnet-4-6"
    embedding_model: str = "text-embedding-3-small"
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "false"
    langchain_project: str = "synapse"
    mem0_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
