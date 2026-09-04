"""
FastAPI REST backend for the Inventory Management System.

Architecture: Streamlit UI -> FastAPI REST -> inventory_service.py -> SQLAlchemy -> SQLite.
Every endpoint is a thin wrapper around a pure function in
``src/inventory_service.py`` — no business logic lives here, only
HTTP concerns (status codes, request/response shapes, session lifecycle).

Run with: uvicorn api.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src import inventory_service as service
from src.database import get_session_factory, init_db
from src.exceptions import InventoryError

_session_factory = None


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _session_factory
    init_db()
    _session_factory = get_session_factory()
    yield


app = FastAPI(title="Inventory Management System API", version="1.0.0", lifespan=_lifespan)


def get_db() -> Session:
    """FastAPI dependency yielding a request-scoped database session."""
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# --- Request/response schemas --------------------------------------------------

class CategoryCreate(BaseModel):
    name: str


class SupplierCreate(BaseModel):
    name: str
    contact_email: str
    contact_phone: str = ""


class ProductCreate(BaseModel):
    sku: str
    name: str
    category_id: int
    supplier_id: int
    quantity_on_hand: int = 0
    unit_price_cents: int = 0
    low_stock_threshold: int = 10


class StockAdjustment(BaseModel):
    delta: int = Field(..., description="Positive to add stock, negative to remove.")


class PurchaseOrderLineCreate(BaseModel):
    product_id: int
    quantity: int
    unit_cost_cents: int


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    lines: list[PurchaseOrderLineCreate]


def _product_to_dict(p) -> dict:
    return {
        "product_id": p.product_id, "sku": p.sku, "name": p.name,
        "quantity_on_hand": p.quantity_on_hand, "unit_price_cents": p.unit_price_cents,
        "low_stock_threshold": p.low_stock_threshold, "is_low_stock": p.is_low_stock,
        "category_id": p.category_id, "supplier_id": p.supplier_id,
    }


# --- Error handling ------------------------------------------------------------

@app.exception_handler(InventoryError)
async def _handle_inventory_error(_request, exc: InventoryError):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=400, content={"detail": str(exc)})


# --- Category endpoints ------------------------------------------------------------

@app.post("/categories")
def create_category(body: CategoryCreate, db: Session = Depends(get_db)):
    category = service.create_category(db, body.name)
    return {"category_id": category.category_id, "name": category.name}


@app.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    return [{"category_id": c.category_id, "name": c.name} for c in service.list_categories(db)]


# --- Supplier endpoints -------------------------------------------------------------

@app.post("/suppliers")
def create_supplier(body: SupplierCreate, db: Session = Depends(get_db)):
    supplier = service.create_supplier(db, body.name, body.contact_email, body.contact_phone)
    return {"supplier_id": supplier.supplier_id, "name": supplier.name, "contact_email": supplier.contact_email}


@app.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db)):
    return [
        {"supplier_id": s.supplier_id, "name": s.name, "contact_email": s.contact_email, "contact_phone": s.contact_phone}
        for s in service.list_suppliers(db)
    ]


# --- Product endpoints ---------------------------------------------------------------

@app.post("/products")
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    product = service.create_product(
        db, body.sku, body.name, body.category_id, body.supplier_id,
        body.quantity_on_hand, body.unit_price_cents, body.low_stock_threshold,
    )
    return _product_to_dict(product)


@app.get("/products")
def list_products(category_id: int | None = None, db: Session = Depends(get_db)):
    return [_product_to_dict(p) for p in service.list_products(db, category_id=category_id)]


@app.get("/products/low-stock")
def low_stock_products(db: Session = Depends(get_db)):
    return [_product_to_dict(p) for p in service.get_low_stock_products(db)]


@app.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    return _product_to_dict(service.get_product(db, product_id))


@app.post("/products/{product_id}/adjust-stock")
def adjust_stock(product_id: int, body: StockAdjustment, db: Session = Depends(get_db)):
    return _product_to_dict(service.adjust_stock(db, product_id, body.delta))


# --- Purchase order endpoints -------------------------------------------------------

@app.post("/purchase-orders")
def create_purchase_order(body: PurchaseOrderCreate, db: Session = Depends(get_db)):
    lines = [
        service.PurchaseOrderLineRequest(product_id=l.product_id, quantity=l.quantity, unit_cost_cents=l.unit_cost_cents)
        for l in body.lines
    ]
    order = service.create_purchase_order(db, body.supplier_id, lines)
    return {
        "purchase_order_id": order.purchase_order_id, "supplier_id": order.supplier_id,
        "status": order.status, "total_cost_cents": order.total_cost_cents,
        "items": [{"product_id": i.product_id, "quantity": i.quantity, "unit_cost_cents": i.unit_cost_cents} for i in order.items],
    }


@app.post("/purchase-orders/{purchase_order_id}/receive")
def receive_purchase_order(purchase_order_id: int, db: Session = Depends(get_db)):
    order = service.receive_purchase_order(db, purchase_order_id)
    return {"purchase_order_id": order.purchase_order_id, "status": order.status}


@app.get("/purchase-orders/reorder-suggestions")
def reorder_suggestions(reorder_quantity: int = 50, db: Session = Depends(get_db)):
    suggestions = service.generate_reorder_suggestions(db, reorder_quantity)
    return [{"product_id": s.product_id, "quantity": s.quantity, "unit_cost_cents": s.unit_cost_cents} for s in suggestions]


# --- Reporting -----------------------------------------------------------------------

@app.get("/reports/inventory")
def inventory_report(db: Session = Depends(get_db)):
    report = service.generate_inventory_report(db)
    return {
        "total_products": report.total_products, "total_units": report.total_units,
        "total_inventory_value_cents": report.total_inventory_value_cents,
        "low_stock_count": report.low_stock_count, "generated_at": report.generated_at.isoformat(),
    }
