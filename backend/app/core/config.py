from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["dev", "prod", "test"] = "dev"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://finagent:finagent@localhost:5432/finagent"

    qdrant_url: str = "http://localhost:6333"

    llm_provider: Literal["openai", "ollama"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral"

    statements_dir: str = "./data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
