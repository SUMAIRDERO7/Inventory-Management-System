"""
Tests for api/main.py — real HTTP-layer tests via FastAPI's TestClient.

Uses a fresh in-memory SQLite database per test (via FastAPI's
``dependency_overrides``), so these never touch the real
``data/inventory.db`` file and never leak state between tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app, get_db
from src.database import get_session_factory, init_db


@pytest.fixture
def client(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test_inventory.db"
    init_db(db_url)
    session_factory = get_session_factory(db_url)

    def _override_get_db():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def category_id(client) -> int:
    return client.post("/categories", json={"name": "Electronics"}).json()["category_id"]


@pytest.fixture
def supplier_id(client) -> int:
    return client.post(
        "/suppliers", json={"name": "Acme Supply Co", "contact_email": "orders@acme.test"}
    ).json()["supplier_id"]


class TestCategoryEndpoints:
    def test_create_and_list_category(self, client) -> None:
        response = client.post("/categories", json={"name": "Office Supplies"})
        assert response.status_code == 200
        assert response.json()["name"] == "Office Supplies"

        listing = client.get("/categories").json()
        assert any(c["name"] == "Office Supplies" for c in listing)


class TestSupplierEndpoints:
    def test_create_and_list_supplier(self, client) -> None:
        response = client.post(
            "/suppliers", json={"name": "Globex", "contact_email": "hi@globex.test", "contact_phone": "555-0100"}
        )
        assert response.status_code == 200
        assert response.json()["contact_email"] == "hi@globex.test"

        listing = client.get("/suppliers").json()
        assert any(s["name"] == "Globex" for s in listing)


class TestProductEndpoints:
    def test_create_product(self, client, category_id, supplier_id) -> None:
        response = client.post(
            "/products",
            json={
                "sku": "SKU-001", "name": "USB Cable", "category_id": category_id,
                "supplier_id": supplier_id, "quantity_on_hand": 100, "unit_price_cents": 599,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["sku"] == "SKU-001"
        assert body["is_low_stock"] is False

    def test_duplicate_sku_returns_400(self, client, category_id, supplier_id) -> None:
        payload = {
            "sku": "SKU-DUPE", "name": "Widget", "category_id": category_id,
            "supplier_id": supplier_id, "quantity_on_hand": 10, "unit_price_cents": 100,
        }
        client.post("/products", json=payload)
        response = client.post("/products", json=payload)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_unknown_category_returns_400_not_500(self, client, supplier_id) -> None:
        response = client.post(
            "/products",
            json={
                "sku": "SKU-002", "name": "Widget", "category_id": 9999,
                "supplier_id": supplier_id, "quantity_on_hand": 10, "unit_price_cents": 100,
            },
        )
        assert response.status_code == 400  # a business-rule violation, not a server crash

    def test_get_product_by_id(self, client, category_id, supplier_id) -> None:
        created = client.post(
            "/products",
            json={
                "sku": "SKU-003", "name": "Cable", "category_id": category_id,
                "supplier_id": supplier_id, "quantity_on_hand": 5, "unit_price_cents": 250,
            },
        ).json()
        response = client.get(f"/products/{created['product_id']}")
        assert response.status_code == 200
        assert response.json()["sku"] == "SKU-003"

    def test_get_unknown_product_returns_400(self, client) -> None:
        response = client.get("/products/99999")
        assert response.status_code == 400

    def test_low_stock_endpoint_reflects_threshold(self, client, category_id, supplier_id) -> None:
        client.post(
            "/products",
            json={
                "sku": "SKU-LOW", "name": "Nearly Out", "category_id": category_id,
                "supplier_id": supplier_id, "quantity_on_hand": 2, "unit_price_cents": 100,
                "low_stock_threshold": 10,
            },
        )
        response = client.get("/products/low-stock")
        assert any(p["sku"] == "SKU-LOW" for p in response.json())

    def test_low_stock_route_not_shadowed_by_product_id_route(self, client) -> None:
        # Regression-style check: /products/low-stock must resolve to the
        # low-stock endpoint, not be swallowed by /products/{product_id}
        # trying (and failing) to parse "low-stock" as an integer ID.
        response = client.get("/products/low-stock")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_adjust_stock_increases_quantity(self, client, category_id, supplier_id) -> None:
        product = client.post(
            "/products",
            json={
                "sku": "SKU-ADJ", "name": "Adjustable", "category_id": category_id,
                "supplier_id": supplier_id, "quantity_on_hand": 10, "unit_price_cents": 100,
            },
        ).json()
        response = client.post(f"/products/{product['product_id']}/adjust-stock", json={"delta": 5})
        assert response.json()["quantity_on_hand"] == 15

    def test_adjust_stock_below_zero_returns_400(self, client, category_id, supplier_id) -> None:
        product = client.post(
            "/products",
            json={
                "sku": "SKU-NEG", "name": "Low Stock Item", "category_id": category_id,
                "supplier_id": supplier_id, "quantity_on_hand": 3, "unit_price_cents": 100,
            },
        ).json()
        response = client.post(f"/products/{product['product_id']}/adjust-stock", json={"delta": -10})
        assert response.status_code == 400


class TestPurchaseOrderEndpoints:
    def test_create_and_receive_purchase_order(self, client, category_id, supplier_id) -> None:
        product = client.post(
            "/products",
            json={
                "sku": "SKU-PO", "name": "Reorderable", "category_id": category_id,
                "supplier_id": supplier_id, "quantity_on_hand": 5, "unit_price_cents": 200,
            },
        ).json()

        order = client.post(
            "/purchase-orders",
            json={"supplier_id": supplier_id, "lines": [{"product_id": product["product_id"], "quantity": 20, "unit_cost_cents": 180}]},
        ).json()
        assert order["status"] == "pending"
        assert order["total_cost_cents"] == 20 * 180

        received = client.post(f"/purchase-orders/{order['purchase_order_id']}/receive").json()
        assert received["status"] == "received"

        updated_product = client.get(f"/products/{product['product_id']}").json()
        assert updated_product["quantity_on_hand"] == 25  # 5 + 20

    def test_reorder_suggestions_endpoint(self, client, category_id, supplier_id) -> None:
        client.post(
            "/products",
            json={
                "sku": "SKU-REORD", "name": "Almost Empty", "category_id": category_id,
                "supplier_id": supplier_id, "quantity_on_hand": 1, "unit_price_cents": 300,
                "low_stock_threshold": 10,
            },
        )
        response = client.get("/purchase-orders/reorder-suggestions?reorder_quantity=25")
        suggestions = response.json()
        assert any(s["quantity"] == 25 for s in suggestions)


class TestReportEndpoint:
    def test_inventory_report_reflects_created_products(self, client, category_id, supplier_id) -> None:
        client.post(
            "/products",
            json={
                "sku": "SKU-RPT", "name": "Reported", "category_id": category_id,
                "supplier_id": supplier_id, "quantity_on_hand": 10, "unit_price_cents": 500,
            },
        )
        report = client.get("/reports/inventory").json()
        assert report["total_products"] >= 1
        assert report["total_units"] >= 10
