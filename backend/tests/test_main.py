from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_shape():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"llm", "postgres", "qdrant", "tesseract", "statementsDir"}
    assert set(body["llm"].keys()) == {"provider", "ok", "model", "detail"}
    assert set(body["postgres"].keys()) == {"ok", "detail"}
