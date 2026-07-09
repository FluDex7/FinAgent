"""Dev-only offline eval harness for the FinAgent agent (Ragas + MLflow).

Not part of the product: nothing in app/ imports this package. Run with
`uv run python -m evals` from backend/ — see README «Agent Quality Evals».

Importing this package installs a small compatibility shim: ragas 0.4.x
still imports `langchain_community.chat_models.vertexai` at module import
time, but langchain-community 0.4 removed that module (Vertex AI moved to
langchain-google-vertexai years ago). FinAgent never touches Vertex AI, so
a placeholder module keeps ragas importable without downgrading the app's
real langchain dependencies for the sake of a dev tool.
"""

import sys
import types


def _install_ragas_langchain_shim() -> None:
    try:
        import langchain_community.chat_models.vertexai  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("langchain_community.chat_models.vertexai")
        stub.ChatVertexAI = type("ChatVertexAI", (), {})  # type: ignore[attr-defined]
        sys.modules["langchain_community.chat_models.vertexai"] = stub


_install_ragas_langchain_shim()
