"""
SQLAlchemy 2.0 ORM models for the Inventory Management System.

Uses the modern ``Mapped``/``mapped_column`` declarative style
(SQLAlchemy 2.0), consistent with the Personal Finance Manager
project's ORM conventions earlier in this portfolio.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    """Return the current UTC time (used as a default factory, so it's
    evaluated per-row, not once at import time)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all ORM models in this project."""


class Category(Base):
    """A product category (e.g. 'Electronics', 'Office Supplies')."""

    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Supplier(Base):
    """A supplier/vendor a product can be reordered from."""

    __tablename__ = "suppliers"

    supplier_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    contact_email: Mapped[str] = mapped_column(String(150))
    contact_phone: Mapped[str] = mapped_column(String(50), default="")

    products: Mapped[list["Product"]] = relationship(back_populates="supplier")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="supplier")


class Product(Base):
    """A single inventory item."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("sku", name="uq_products_sku"),)

    product_id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    quantity_on_hand: Mapped[int] = mapped_column(default=0)
    unit_price_cents: Mapped[int] = mapped_column(default=0)
    low_stock_threshold: Mapped[int] = mapped_column(default=10)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.supplier_id"))

    category: Mapped["Category"] = relationship(back_populates="products")
    supplier: Mapped["Supplier"] = relationship(back_populates="products")

    @property
    def is_low_stock(self) -> bool:
        """True if quantity on hand is at or below the low-stock threshold."""
        return self.quantity_on_hand <= self.low_stock_threshold

    @property
    def unit_price_dollars(self) -> float:
        """Unit price as a dollar float, converted from integer cents.

        Storing money as integer cents (not float dollars) avoids
        floating-point rounding drift across many transactions — a
        deliberate choice, not an oversight. See README.
        """
        return self.unit_price_cents / 100


class PurchaseOrder(Base):
    """A purchase order placed with a supplier to restock one or more products."""

    __tablename__ = "purchase_orders"

    purchase_order_id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.supplier_id"))
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | received | cancelled

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )

    @property
    def total_cost_cents(self) -> int:
        """Total cost of every line item on this order, in integer cents."""
        return sum(item.quantity * item.unit_cost_cents for item in self.items)


class PurchaseOrderItem(Base):
    """A single product line on a purchase order."""

    __tablename__ = "purchase_order_items"

    purchase_order_item_id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.purchase_order_id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    quantity: Mapped[int]
    unit_cost_cents: Mapped[int]

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
