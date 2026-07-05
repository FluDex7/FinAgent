import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

CSV_CONTENT = (
    b"date,amount,description\n"
    b"2025-01-14,-540.00,PYATEROCHKA 5443\n"
    b"2025-01-15,-1200.50,YANDEX.TAXI\n"
)


@pytest.fixture
def client(tmp_path):
    def override_settings() -> Settings:
        return Settings(statements_dir=str(tmp_path))

    app.dependency_overrides[get_settings] = override_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_upload_tree_transactions_delete_flow(client: TestClient):
    folder = f"pytest-{uuid.uuid4().hex[:8]}"

    upload_resp = client.post(
        "/statements",
        files={"file": ("q1.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
        data={"folder": folder},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    statement = upload_resp.json()
    assert statement["status"] == "parsed"
    assert statement["transactionCount"] == 2
    statement_id = statement["id"]

    tree_resp = client.get("/documents/tree")
    assert tree_resp.status_code == 200
    tree = tree_resp.json()
    matching = [f for folder_ in tree for f in folder_["files"] if f["id"] == statement_id]
    assert len(matching) == 1
    assert matching[0]["status"] == "parsed"
    assert matching[0]["txCount"] == 2

    get_resp = client.get(f"/statements/{statement_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["folderPath"] == folder

    tx_resp = client.get(f"/statements/{statement_id}/transactions")
    assert tx_resp.status_code == 200
    transactions = tx_resp.json()
    assert len(transactions) == 2
    assert transactions[0]["rawDescription"] == "PYATEROCHKA 5443"

    delete_resp = client.delete(f"/statements/{statement_id}")
    assert delete_resp.status_code == 204

    get_after_delete = client.get(f"/statements/{statement_id}")
    assert get_after_delete.status_code == 404


def test_upload_unsupported_format_returns_422(client: TestClient):
    resp = client.post(
        "/statements",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"folder": "misc"},
    )
    assert resp.status_code == 422
    assert resp.json()["hint"]


def test_get_missing_statement_returns_404(client: TestClient):
    resp = client.get(f"/statements/{uuid.uuid4()}")
    assert resp.status_code == 404
