"""Tests for src/inventory_service.py."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src import inventory_service as service
from src.database import init_db, make_engine
from src.exceptions import (
    CategoryNotFoundError,
    DuplicateSKUError,
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotFoundError,
    PurchaseOrderNotFoundError,
    SupplierNotFoundError,
)


@pytest.fixture
def db_session():
    engine = make_engine("sqlite:///:memory:")
    from src.models import Base

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def category(db_session):
    return service.create_category(db_session, "Electronics")


@pytest.fixture
def supplier(db_session):
    return service.create_supplier(db_session, "Acme Supply Co", "orders@acme.example")


class TestCreateCategory:
    def test_creates_category(self, db_session) -> None:
        category = service.create_category(db_session, "Office Supplies")
        assert category.category_id is not None
        assert category.name == "Office Supplies"


class TestCreateSupplier:
    def test_creates_supplier(self, db_session) -> None:
        supplier = service.create_supplier(db_session, "Vendor Inc", "sales@vendor.example", "555-1234")
        assert supplier.supplier_id is not None
        assert supplier.contact_phone == "555-1234"

    def test_get_supplier_raises_for_unknown_id(self, db_session) -> None:
        with pytest.raises(SupplierNotFoundError):
            service.get_supplier(db_session, 999)


class TestCreateProduct:
    def test_creates_product(self, db_session, category, supplier) -> None:
        product = service.create_product(
            db_session, "SKU-001", "Wireless Mouse", category.category_id, supplier.supplier_id,
            quantity_on_hand=25, unit_price_cents=1999,
        )
        assert product.product_id is not None
        assert product.sku == "SKU-001"
        assert product.unit_price_dollars == 19.99

    def test_rejects_negative_quantity(self, db_session, category, supplier) -> None:
        with pytest.raises(InvalidQuantityError):
            service.create_product(db_session, "SKU-002", "X", category.category_id, supplier.supplier_id, quantity_on_hand=-1)

    def test_rejects_unknown_category(self, db_session, supplier) -> None:
        with pytest.raises(CategoryNotFoundError):
            service.create_product(db_session, "SKU-003", "X", 999, supplier.supplier_id)

    def test_rejects_unknown_supplier(self, db_session, category) -> None:
        with pytest.raises(SupplierNotFoundError):
            service.create_product(db_session, "SKU-004", "X", category.category_id, 999)

    def test_rejects_duplicate_sku(self, db_session, category, supplier) -> None:
        service.create_product(db_session, "SKU-005", "First", category.category_id, supplier.supplier_id)
        with pytest.raises(DuplicateSKUError):
            service.create_product(db_session, "SKU-005", "Second", category.category_id, supplier.supplier_id)


class TestAdjustStock:
    def test_increases_stock(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-010", "X", category.category_id, supplier.supplier_id, quantity_on_hand=10)
        updated = service.adjust_stock(db_session, product.product_id, 5)
        assert updated.quantity_on_hand == 15

    def test_decreases_stock(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-011", "X", category.category_id, supplier.supplier_id, quantity_on_hand=10)
        updated = service.adjust_stock(db_session, product.product_id, -4)
        assert updated.quantity_on_hand == 6

    def test_raises_when_going_below_zero(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-012", "X", category.category_id, supplier.supplier_id, quantity_on_hand=3)
        with pytest.raises(InsufficientStockError):
            service.adjust_stock(db_session, product.product_id, -10)

    def test_exactly_zero_is_allowed(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-013", "X", category.category_id, supplier.supplier_id, quantity_on_hand=5)
        updated = service.adjust_stock(db_session, product.product_id, -5)
        assert updated.quantity_on_hand == 0

    def test_raises_for_unknown_product(self, db_session) -> None:
        with pytest.raises(ProductNotFoundError):
            service.adjust_stock(db_session, 999, 1)


class TestLowStockDetection:
    def test_flags_product_at_or_below_threshold(self, db_session, category, supplier) -> None:
        service.create_product(
            db_session, "SKU-020", "Low Item", category.category_id, supplier.supplier_id,
            quantity_on_hand=5, low_stock_threshold=10,
        )
        low_stock = service.get_low_stock_products(db_session)
        assert len(low_stock) == 1
        assert low_stock[0].sku == "SKU-020"

    def test_does_not_flag_product_above_threshold(self, db_session, category, supplier) -> None:
        service.create_product(
            db_session, "SKU-021", "Healthy Item", category.category_id, supplier.supplier_id,
            quantity_on_hand=50, low_stock_threshold=10,
        )
        assert service.get_low_stock_products(db_session) == []

    def test_exactly_at_threshold_is_flagged(self, db_session, category, supplier) -> None:
        service.create_product(
            db_session, "SKU-022", "Boundary Item", category.category_id, supplier.supplier_id,
            quantity_on_hand=10, low_stock_threshold=10,
        )
        assert len(service.get_low_stock_products(db_session)) == 1

    def test_worst_shortfall_sorted_first(self, db_session, category, supplier) -> None:
        service.create_product(db_session, "SKU-023", "Mild", category.category_id, supplier.supplier_id, quantity_on_hand=9, low_stock_threshold=10)
        service.create_product(db_session, "SKU-024", "Severe", category.category_id, supplier.supplier_id, quantity_on_hand=0, low_stock_threshold=10)
        low_stock = service.get_low_stock_products(db_session)
        assert low_stock[0].sku == "SKU-024"


class TestPurchaseOrders:
    def test_creates_order_with_line_items(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-030", "X", category.category_id, supplier.supplier_id)
        lines = [service.PurchaseOrderLineRequest(product_id=product.product_id, quantity=20, unit_cost_cents=500)]

        order = service.create_purchase_order(db_session, supplier.supplier_id, lines)

        assert order.purchase_order_id is not None
        assert order.status == "pending"
        assert order.total_cost_cents == 10000

    def test_rejects_empty_line_list(self, db_session, supplier) -> None:
        with pytest.raises(InvalidQuantityError):
            service.create_purchase_order(db_session, supplier.supplier_id, [])

    def test_rejects_nonpositive_quantity(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-031", "X", category.category_id, supplier.supplier_id)
        lines = [service.PurchaseOrderLineRequest(product_id=product.product_id, quantity=0, unit_cost_cents=500)]
        with pytest.raises(InvalidQuantityError):
            service.create_purchase_order(db_session, supplier.supplier_id, lines)

    def test_rejects_unknown_supplier(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-032", "X", category.category_id, supplier.supplier_id)
        lines = [service.PurchaseOrderLineRequest(product_id=product.product_id, quantity=5, unit_cost_cents=500)]
        with pytest.raises(SupplierNotFoundError):
            service.create_purchase_order(db_session, 999, lines)

    def test_receiving_order_increases_stock(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-033", "X", category.category_id, supplier.supplier_id, quantity_on_hand=5)
        lines = [service.PurchaseOrderLineRequest(product_id=product.product_id, quantity=20, unit_cost_cents=500)]
        order = service.create_purchase_order(db_session, supplier.supplier_id, lines)

        service.receive_purchase_order(db_session, order.purchase_order_id)

        refreshed = service.get_product(db_session, product.product_id)
        assert refreshed.quantity_on_hand == 25

    def test_receiving_order_marks_it_received(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-034", "X", category.category_id, supplier.supplier_id)
        lines = [service.PurchaseOrderLineRequest(product_id=product.product_id, quantity=1, unit_cost_cents=100)]
        order = service.create_purchase_order(db_session, supplier.supplier_id, lines)

        updated = service.receive_purchase_order(db_session, order.purchase_order_id)

        assert updated.status == "received"

    def test_cannot_receive_order_twice(self, db_session, category, supplier) -> None:
        product = service.create_product(db_session, "SKU-035", "X", category.category_id, supplier.supplier_id)
        lines = [service.PurchaseOrderLineRequest(product_id=product.product_id, quantity=1, unit_cost_cents=100)]
        order = service.create_purchase_order(db_session, supplier.supplier_id, lines)
        service.receive_purchase_order(db_session, order.purchase_order_id)

        with pytest.raises(InvalidQuantityError):
            service.receive_purchase_order(db_session, order.purchase_order_id)

    def test_receiving_unknown_order_raises(self, db_session) -> None:
        with pytest.raises(PurchaseOrderNotFoundError):
            service.receive_purchase_order(db_session, 999)


class TestReorderSuggestions:
    def test_suggests_only_low_stock_products(self, db_session, category, supplier) -> None:
        service.create_product(db_session, "SKU-040", "Low", category.category_id, supplier.supplier_id, quantity_on_hand=2, low_stock_threshold=10, unit_price_cents=500)
        service.create_product(db_session, "SKU-041", "Healthy", category.category_id, supplier.supplier_id, quantity_on_hand=100, low_stock_threshold=10)

        suggestions = service.generate_reorder_suggestions(db_session, reorder_quantity=30)

        assert len(suggestions) == 1
        assert suggestions[0].quantity == 30
        assert suggestions[0].unit_cost_cents == 500

    def test_no_low_stock_gives_no_suggestions(self, db_session, category, supplier) -> None:
        service.create_product(db_session, "SKU-042", "Healthy", category.category_id, supplier.supplier_id, quantity_on_hand=100, low_stock_threshold=10)
        assert service.generate_reorder_suggestions(db_session) == []


class TestInventoryReport:
    def test_report_reflects_real_totals(self, db_session, category, supplier) -> None:
        service.create_product(db_session, "SKU-050", "A", category.category_id, supplier.supplier_id, quantity_on_hand=50, unit_price_cents=100, low_stock_threshold=10)
        service.create_product(db_session, "SKU-051", "B", category.category_id, supplier.supplier_id, quantity_on_hand=5, unit_price_cents=200, low_stock_threshold=10)

        report = service.generate_inventory_report(db_session)

        assert report.total_products == 2
        assert report.total_units == 55
        assert report.total_inventory_value_cents == 50 * 100 + 5 * 200
        assert report.low_stock_count == 1

    def test_empty_inventory_reports_zeros(self, db_session) -> None:
        report = service.generate_inventory_report(db_session)
        assert report.total_products == 0
        assert report.total_units == 0
        assert report.total_inventory_value_cents == 0
