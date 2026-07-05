import logging

import mlflow

from app.core.config import Settings

logger = logging.getLogger(__name__)

_configured = False


def setup_tracing(settings: Settings) -> None:
    """Enables MLflow tracing of every LangGraph/LangChain call the agent makes.

    Local-only by default (sqlite:///./mlflow.db) — inspect traces with
    `uv run mlflow ui --backend-store-uri sqlite:///./mlflow.db`.
    """
    global _configured
    if _configured:
        return

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)
    mlflow.langchain.autolog()
    _configured = True
    logger.info(
        "MLflow tracing enabled (%s, experiment=%s)",
        settings.mlflow_tracking_uri,
        settings.mlflow_experiment_name,
    )
