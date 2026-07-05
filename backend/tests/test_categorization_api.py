import io
import random
import string
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def _unique_merchant_name() -> str:
    # normalize_merchant() only keeps a leading run of letters/spaces, so digits
    # (e.g. from a uuid) would truncate this — pure letters keep it unique instead.
    return "UNKNOWN SHOP " + "".join(random.choices(string.ascii_uppercase, k=10))


@pytest.fixture
def client(tmp_path):
    def override_settings() -> Settings:
        return Settings(statements_dir=str(tmp_path))

    app.dependency_overrides[get_settings] = override_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_categories_includes_seeded_defaults(client: TestClient):
    resp = client.get("/categories")
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()}
    assert "Продукты" in names
    assert "Прочее" in names


def test_create_and_update_category(client: TestClient):
    suffix = uuid.uuid4().hex[:6]
    create_resp = client.post("/categories", json={"name": f"Тест-{suffix}"})
    assert create_resp.status_code == 200
    category = create_resp.json()

    update_resp = client.patch(
        f"/categories/{category['id']}",
        json={"name": f"Обновлено-{suffix}", "color": "#112233"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == f"Обновлено-{suffix}"
    assert updated["color"] == "#112233"


def test_update_unknown_category_returns_404(client: TestClient):
    resp = client.patch(f"/categories/{uuid.uuid4()}", json={"name": "x"})
    assert resp.status_code == 404


def test_recategorize_merchant_via_api(client: TestClient):
    folder = f"pytest-cat-{uuid.uuid4().hex[:8]}"
    csv_content = (
        f"date,amount,description\n2025-01-14,-10.00,{_unique_merchant_name()}\n"
    ).encode()
    upload_resp = client.post(
        "/statements",
        files={"file": ("q.csv", io.BytesIO(csv_content), "text/csv")},
        data={"folder": folder},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    statement_id = upload_resp.json()["id"]

    tx_resp = client.get(f"/statements/{statement_id}/transactions")
    transaction = tx_resp.json()[0]
    merchant_id = transaction["merchantId"]
    assert merchant_id is not None

    review_resp = client.get("/categories/merchants", params={"needs_review": True})
    assert review_resp.status_code == 200
    assert any(m["id"] == merchant_id for m in review_resp.json())

    categories = client.get("/categories").json()
    target_category = next(c for c in categories if c["name"] == "Кафе и рестораны")

    recat_resp = client.patch(
        f"/categories/merchants/{merchant_id}", json={"categoryId": target_category["id"]}
    )
    assert recat_resp.status_code == 200
    assert recat_resp.json()["categoryId"] == target_category["id"]
    assert recat_resp.json()["source"] == "user"

    tx_after = client.get(f"/statements/{statement_id}/transactions").json()[0]
    assert tx_after["categoryId"] == target_category["id"]

    client.delete(f"/statements/{statement_id}")


def test_recategorize_unknown_merchant_returns_404(client: TestClient):
    categories = client.get("/categories").json()
    category_id = categories[0]["id"]

    resp = client.patch(
        f"/categories/merchants/{uuid.uuid4()}", json={"categoryId": category_id}
    )
    assert resp.status_code == 404
