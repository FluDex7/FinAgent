import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.core.config import Settings, get_settings
from app.main import app
from app.modules.agent import service as service_module
from app.modules.agent.tests.fakes import FakeToolCallingChatModel


@pytest.fixture
def client(monkeypatch, tmp_path):
    fake = FakeToolCallingChatModel(responses=[AIMessage(content="Привет из API")])
    monkeypatch.setattr(service_module, "get_chat_model", lambda settings: fake)

    def override_settings() -> Settings:
        return Settings(statements_dir=str(tmp_path), agent_self_check=False)

    app.dependency_overrides[get_settings] = override_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _parse_sse(raw: str) -> list[dict]:
    events = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event_type = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append({"event": event_type, "data": data})
    return events


def test_chat_endpoint_streams_sse_events(client: TestClient):
    resp = client.post("/chat", json={"message": "привет"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    kinds = [e["event"] for e in events]
    assert kinds[0] == "chat"
    assert kinds[-1] == "done"
    assert "token" in kinds

    chat_id = events[0]["data"]["chatId"]

    messages_resp = client.get(f"/chats/{chat_id}/messages")
    assert messages_resp.status_code == 200
    messages = messages_resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"

    client.delete(f"/chats/{chat_id}")


def test_chats_crud_via_api(client: TestClient):
    create_resp = client.post("/chats")
    assert create_resp.status_code == 200
    chat_id = create_resp.json()["id"]

    list_resp = client.get("/chats")
    assert any(c["id"] == chat_id for c in list_resp.json())

    rename_resp = client.patch(f"/chats/{chat_id}", json={"title": "Переименовано"})
    assert rename_resp.json()["title"] == "Переименовано"

    delete_resp = client.delete(f"/chats/{chat_id}")
    assert delete_resp.status_code == 204

    missing_resp = client.get(f"/chats/{chat_id}/messages")
    assert missing_resp.status_code == 404
