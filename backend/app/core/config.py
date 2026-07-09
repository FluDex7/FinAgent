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

    mlflow_tracking_uri: str = "sqlite:///./mlflow.db"
    mlflow_experiment_name: str = "finagent"

    ui_url: str = "http://localhost:3000"

    # Optional — the one outbound call FinAgent makes to a third party. Only enabled
    # when set; the agent is told to use it strictly for things it can't know locally
    # (exchange rates, current events), never with the user's own financial data.
    tavily_api_key: str | None = None

    # Critic pass over every answer before it reaches the user: catches wrong-language
    # replies, broad questions answered without a chart/period, transfers passed off
    # as spending, leaked SQL — and sends the answer back for one revision. Costs one
    # extra LLM call per turn (two when a revision happens); turn off to save it.
    agent_self_check: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
