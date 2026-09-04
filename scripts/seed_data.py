"""
Seed the database with realistic demo data.

Run with: python scripts/seed_data.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import inventory_service as service  # noqa: E402
from src.database import get_session_factory, init_db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

_CATEGORIES = ["Electronics", "Office Supplies", "Packaging", "Cleaning Supplies"]

_SUPPLIERS = [
    ("TechSource Wholesale", "orders@techsource.example", "555-0101"),
    ("OfficeDirect Ltd", "sales@officedirect.example", "555-0102"),
    ("PackRight Co", "hello@packright.example", "555-0103"),
]

# (sku, name, category, supplier_index, quantity, price_cents, low_stock_threshold)
_PRODUCTS = [
    ("ELEC-001", "USB-C Cable 2m", "Electronics", 0, 8, 799, 15),      # low stock on purpose
    ("ELEC-002", "Wireless Mouse", "Electronics", 0, 120, 1999, 20),
    ("ELEC-003", "HDMI Adapter", "Electronics", 0, 5, 1299, 10),        # low stock on purpose
    ("OFF-001", "A4 Paper Ream", "Office Supplies", 1, 300, 549, 50),
    ("OFF-002", "Stapler", "Office Supplies", 1, 45, 899, 10),
    ("OFF-003", "Sticky Notes Pack", "Office Supplies", 1, 12, 349, 20),  # low stock on purpose
    ("PKG-001", "Shipping Box (Medium)", "Packaging", 2, 500, 129, 100),
    ("PKG-002", "Bubble Wrap Roll", "Packaging", 2, 30, 1499, 15),
    ("CLN-001", "Disinfectant Spray", "Cleaning Supplies", 1, 60, 649, 20),
]


def seed(database_url: str | None = None) -> None:
    """Populate the database with demo categories, suppliers, and products.

    Args:
        database_url: Optional override; defaults to ``config.DATABASE_URL``.
    """
    if database_url:
        init_db(database_url)
        session_factory = get_session_factory(database_url)
    else:
        init_db()
        session_factory = get_session_factory()

    with session_factory() as session:
        category_by_name = {}
        for name in _CATEGORIES:
            category_by_name[name] = service.create_category(session, name)

        suppliers = [
            service.create_supplier(session, name, email, phone) for name, email, phone in _SUPPLIERS
        ]

        for sku, name, category_name, supplier_idx, qty, price, threshold in _PRODUCTS:
            service.create_product(
                session,
                sku=sku, name=name,
                category_id=category_by_name[category_name].category_id,
                supplier_id=suppliers[supplier_idx].supplier_id,
                quantity_on_hand=qty, unit_price_cents=price, low_stock_threshold=threshold,
            )

        session.commit()

    logger.info("Seeded %d categories, %d suppliers, %d products", len(_CATEGORIES), len(_SUPPLIERS), len(_PRODUCTS))


if __name__ == "__main__":
    seed()
    print("\nDemo data seeded. Run 'uvicorn api.main:app --reload' then 'streamlit run app.py' to explore it.\n")
