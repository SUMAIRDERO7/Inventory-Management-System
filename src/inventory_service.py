"""
Core inventory business logic.

Every function here takes an explicit ``Session`` argument rather than
managing its own — this is what makes the whole module trivially
testable against an in-memory SQLite database and reusable from both
the FastAPI layer and any future entry point, without either owning
session lifecycle management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.exceptions import (
    CategoryNotFoundError,
    DuplicateSKUError,
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotFoundError,
    PurchaseOrderNotFoundError,
    SupplierNotFoundError,
)
from src.models import Category, Product, PurchaseOrder, PurchaseOrderItem, Supplier

logger = logging.getLogger(__name__)


# --- Categories ----------------------------------------------------------------

def create_category(session: Session, name: str) -> Category:
    """Create a new product category.

    Args:
        session: An active database session.
        name: The category name.

    Returns:
        The newly created :class:`Category`.
    """
    category = Category(name=name)
    session.add(category)
    session.flush()
    return category


def list_categories(session: Session) -> list[Category]:
    """List every category, alphabetically.

    Args:
        session: An active database session.

    Returns:
        All categories, sorted by name.
    """
    return list(session.scalars(select(Category).order_by(Category.name)))


# --- Suppliers -------------------------------------------------------------------

def create_supplier(session: Session, name: str, contact_email: str, contact_phone: str = "") -> Supplier:
    """Create a new supplier.

    Args:
        session: An active database session.
        name: Supplier/vendor name.
        contact_email: Contact email address.
        contact_phone: Contact phone number (optional).

    Returns:
        The newly created :class:`Supplier`.
    """
    supplier = Supplier(name=name, contact_email=contact_email, contact_phone=contact_phone)
    session.add(supplier)
    session.flush()
    return supplier


def list_suppliers(session: Session) -> list[Supplier]:
    """List every supplier, alphabetically.

    Args:
        session: An active database session.

    Returns:
        All suppliers, sorted by name.
    """
    return list(session.scalars(select(Supplier).order_by(Supplier.name)))


def get_supplier(session: Session, supplier_id: int) -> Supplier:
    """Fetch a single supplier by ID.

    Args:
        session: An active database session.
        supplier_id: The supplier's primary key.

    Returns:
        The matching :class:`Supplier`.

    Raises:
        SupplierNotFoundError: If no supplier has that ID.
    """
    supplier = session.get(Supplier, supplier_id)
    if supplier is None:
        raise SupplierNotFoundError(f"No supplier with id {supplier_id}.")
    return supplier


# --- Products ----------------------------------------------------------------------

def create_product(
    session: Session,
    sku: str,
    name: str,
    category_id: int,
    supplier_id: int,
    quantity_on_hand: int = 0,
    unit_price_cents: int = 0,
    low_stock_threshold: int = 10,
) -> Product:
    """Create a new product.

    Args:
        session: An active database session.
        sku: A unique stock-keeping unit code.
        name: Product display name.
        category_id: The owning category's ID.
        supplier_id: The default supplier's ID.
        quantity_on_hand: Starting stock quantity.
        unit_price_cents: Unit price in integer cents.
        low_stock_threshold: Quantity at or below which this product
            is considered low-stock.

    Returns:
        The newly created :class:`Product`.

    Raises:
        CategoryNotFoundError: If ``category_id`` doesn't exist.
        SupplierNotFoundError: If ``supplier_id`` doesn't exist.
        InvalidQuantityError: If ``quantity_on_hand`` is negative.
        DuplicateSKUError: If a product with this SKU already exists.
    """
    if quantity_on_hand < 0:
        raise InvalidQuantityError("quantity_on_hand cannot be negative.")
    if session.get(Category, category_id) is None:
        raise CategoryNotFoundError(f"No category with id {category_id}.")
    if session.get(Supplier, supplier_id) is None:
        raise SupplierNotFoundError(f"No supplier with id {supplier_id}.")
    if session.scalar(select(Product).where(Product.sku == sku)) is not None:
        raise DuplicateSKUError(f"A product with SKU '{sku}' already exists.")

    product = Product(
        sku=sku, name=name, category_id=category_id, supplier_id=supplier_id,
        quantity_on_hand=quantity_on_hand, unit_price_cents=unit_price_cents,
        low_stock_threshold=low_stock_threshold,
    )
    session.add(product)
    session.flush()
    logger.info("Created product '%s' (SKU %s)", name, sku)
    return product


def get_product(session: Session, product_id: int) -> Product:
    """Fetch a single product by ID.

    Args:
        session: An active database session.
        product_id: The product's primary key.

    Returns:
        The matching :class:`Product`.

    Raises:
        ProductNotFoundError: If no product has that ID.
    """
    product = session.get(Product, product_id)
    if product is None:
        raise ProductNotFoundError(f"No product with id {product_id}.")
    return product


def list_products(session: Session, category_id: int | None = None) -> list[Product]:
    """List products, optionally filtered by category.

    Args:
        session: An active database session.
        category_id: If given, only products in this category are returned.

    Returns:
        Matching products, sorted by name.
    """
    stmt = select(Product).order_by(Product.name)
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    return list(session.scalars(stmt))


def adjust_stock(session: Session, product_id: int, delta: int) -> Product:
    """Adjust a product's on-hand quantity by a positive or negative delta.

    Args:
        session: An active database session.
        product_id: The product to adjust.
        delta: The change to apply (negative to remove stock, e.g. a sale).

    Returns:
        The updated :class:`Product`.

    Raises:
        ProductNotFoundError: If no product has that ID.
        InsufficientStockError: If the adjustment would take stock below zero.
    """
    product = get_product(session, product_id)
    new_quantity = product.quantity_on_hand + delta
    if new_quantity < 0:
        raise InsufficientStockError(
            f"Cannot remove {abs(delta)} units from '{product.name}' — only {product.quantity_on_hand} on hand."
        )
    product.quantity_on_hand = new_quantity
    session.flush()
    return product


def get_low_stock_products(session: Session) -> list[Product]:
    """List every product currently at or below its own low-stock threshold.

    Args:
        session: An active database session.

    Returns:
        Low-stock products, worst-shortfall first (lowest quantity relative
        to threshold).
    """
    products = list_products(session)
    low_stock = [p for p in products if p.is_low_stock]
    return sorted(low_stock, key=lambda p: p.quantity_on_hand - p.low_stock_threshold)


# --- Purchase orders -----------------------------------------------------------------

@dataclass(frozen=True)
class PurchaseOrderLineRequest:
    """One requested line item for a new purchase order.

    Attributes:
        product_id: The product to reorder.
        quantity: How many units to order.
        unit_cost_cents: Cost per unit, in integer cents.
    """

    product_id: int
    quantity: int
    unit_cost_cents: int


def create_purchase_order(
    session: Session, supplier_id: int, lines: list[PurchaseOrderLineRequest]
) -> PurchaseOrder:
    """Create a purchase order with one or more line items.

    Args:
        session: An active database session.
        supplier_id: The supplier this order is placed with.
        lines: The requested line items.

    Returns:
        The newly created :class:`PurchaseOrder`, with its items loaded.

    Raises:
        SupplierNotFoundError: If ``supplier_id`` doesn't exist.
        ProductNotFoundError: If any line's ``product_id`` doesn't exist.
        InvalidQuantityError: If any line's quantity isn't positive, or
            ``lines`` is empty.
    """
    if not lines:
        raise InvalidQuantityError("A purchase order needs at least one line item.")
    get_supplier(session, supplier_id)  # raises SupplierNotFoundError if missing

    order = PurchaseOrder(supplier_id=supplier_id, status="pending")
    for line in lines:
        if line.quantity <= 0:
            raise InvalidQuantityError(f"Purchase order quantity must be positive (got {line.quantity}).")
        get_product(session, line.product_id)  # raises ProductNotFoundError if missing
        order.items.append(
            PurchaseOrderItem(product_id=line.product_id, quantity=line.quantity, unit_cost_cents=line.unit_cost_cents)
        )

    session.add(order)
    session.flush()
    logger.info("Created purchase order %d with %d line(s)", order.purchase_order_id, len(lines))
    return order


def generate_reorder_suggestions(
    session: Session, reorder_quantity: int = 50
) -> list[PurchaseOrderLineRequest]:
    """Suggest purchase order line items for every low-stock product,
    reordering from each product's own default supplier at its current price.

    Args:
        session: An active database session.
        reorder_quantity: How many units to suggest reordering per product.

    Returns:
        One suggested line item per low-stock product.
    """
    return [
        PurchaseOrderLineRequest(
            product_id=product.product_id, quantity=reorder_quantity, unit_cost_cents=product.unit_price_cents
        )
        for product in get_low_stock_products(session)
    ]


def receive_purchase_order(session: Session, purchase_order_id: int) -> PurchaseOrder:
    """Mark a purchase order as received and add its quantities to stock.

    Args:
        session: An active database session.
        purchase_order_id: The order to receive.

    Returns:
        The updated :class:`PurchaseOrder`.

    Raises:
        InvalidQuantityError: If the order has already been received or cancelled.
    """
    order = session.get(PurchaseOrder, purchase_order_id)
    if order is None:
        raise PurchaseOrderNotFoundError(f"No purchase order with id {purchase_order_id}.")
    if order.status != "pending":
        raise InvalidQuantityError(f"Purchase order {purchase_order_id} is already '{order.status}'.")

    for item in order.items:
        adjust_stock(session, item.product_id, item.quantity)
    order.status = "received"
    session.flush()
    logger.info("Received purchase order %d", purchase_order_id)
    return order


# --- Reporting -------------------------------------------------------------------------

@dataclass(frozen=True)
class InventoryReport:
    """A point-in-time snapshot of overall inventory health.

    Attributes:
        total_products: Number of distinct products.
        total_units: Sum of quantity_on_hand across all products.
        total_inventory_value_cents: Sum of (quantity * unit price) across all products.
        low_stock_count: Number of products at or below their threshold.
        generated_at: When this report was generated.
    """

    total_products: int
    total_units: int
    total_inventory_value_cents: int
    low_stock_count: int
    generated_at: datetime


def generate_inventory_report(session: Session) -> InventoryReport:
    """Generate a real, computed snapshot of overall inventory health.

    Args:
        session: An active database session.

    Returns:
        An :class:`InventoryReport` computed directly from current data.
    """
    products = list_products(session)
    return InventoryReport(
        total_products=len(products),
        total_units=sum(p.quantity_on_hand for p in products),
        total_inventory_value_cents=sum(p.quantity_on_hand * p.unit_price_cents for p in products),
        low_stock_count=sum(1 for p in products if p.is_low_stock),
        generated_at=datetime.now(timezone.utc),
    )
