"""
Streamlit demo — Inventory Management System "Operations Console".

Layout: a master-detail workspace — a searchable/filterable product
table on the left drives a detail + quick-actions panel on the right,
plus separate tabs for Purchase Orders and Reports. This is the
natural shape for inventory operations (browse, then act on one
item) and a new layout family for this portfolio (Day 36: hero+sidebar
SaaS console, Day 37: score-first review console, Day 40: split-pane
dev workspace — none of those are master-detail).

Talks to the real FastAPI backend over HTTP — this is a genuine
two-service architecture, not a UI calling business logic directly.

Run with:
    uvicorn api.main:app --reload      # in one terminal
    streamlit run app.py                # in another
"""

from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from src.config import (
    API_BASE_URL,
    COLOR_ACCENT,
    COLOR_BACKGROUND,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
)

st.set_page_config(page_title="Inventory Management", page_icon="📦", layout="wide")

st.markdown(
    f"""
    <style>
    .stApp {{ background: {COLOR_BACKGROUND}; }}
    h1, h2, h3, h4 {{ color: {COLOR_TEXT_PRIMARY} !important; font-weight: 700; }}
    p, label, .stMarkdown, span {{ color: {COLOR_TEXT_PRIMARY}; }}
    .subtle {{ color: {COLOR_TEXT_SECONDARY} !important; font-size: 13px; }}

    .hero {{
        background: linear-gradient(120deg, {COLOR_PRIMARY} 0%, {COLOR_SECONDARY} 100%);
        border-radius: 16px; padding: 28px 32px; margin-bottom: 20px;
    }}
    .hero h1, .hero p {{ color: #FFFFFF !important; }}
    .hero .subtitle {{ color: #DCEBFF !important; font-size: 15px; margin-top: 4px; }}

    .kpi-card {{
        background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px;
        padding: 16px 18px; box-shadow: 0 1px 3px rgba(10,37,64,0.06);
    }}
    .kpi-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.5px; color: {COLOR_TEXT_SECONDARY} !important; }}
    .kpi-value {{ font-size: 24px; font-weight: 700; color: {COLOR_PRIMARY} !important; margin-top: 2px; }}

    .detail-panel {{
        background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px;
        padding: 20px; box-shadow: 0 1px 3px rgba(10,37,64,0.06);
    }}
    .stock-badge {{ display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 10px; }}
    .stock-ok {{ background: #D1FAE5; color: #065F46; }}
    .stock-low {{ background: #FEE2E2; color: #991B1B; }}

    .stButton>button {{
        background: {COLOR_SECONDARY}; color: white; border: none; border-radius: 8px;
        font-weight: 600; padding: 0.5rem 1.2rem;
    }}
    .stButton>button:hover {{ background: {COLOR_PRIMARY}; }}

    .footer {{
        margin-top: 36px; padding: 18px 0; border-top: 1px solid {COLOR_BORDER};
        color: {COLOR_TEXT_SECONDARY} !important; font-size: 12px; text-align: center;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>📦 Inventory Management System</h1>
        <p class="subtitle">Streamlit UI → FastAPI REST → SQLAlchemy → SQLite — a real two-service architecture</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def _api_get(path: str, **params):
    try:
        response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=5)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Can't reach the API at {API_BASE_URL}. Is it running? (`uvicorn api.main:app --reload`)"
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.json().get("detail", str(exc)) if exc.response is not None else str(exc)
        return None, detail


def _api_post(path: str, json_body: dict):
    try:
        response = requests.post(f"{API_BASE_URL}{path}", json=json_body, timeout=5)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Can't reach the API at {API_BASE_URL}. Is it running?"
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.json().get("detail", str(exc)) if exc.response is not None else str(exc)
        return None, detail


report, report_err = _api_get("/reports/inventory")
if report_err:
    st.error(f"❌ {report_err}")
    st.info("👉 Run `python scripts/seed_data.py` once to load demo data, then start the API server.")
    st.stop()

kpi_cols = st.columns(4)
kpi_cols[0].markdown(
    f'<div class="kpi-card"><div class="kpi-label">Total Products</div>'
    f'<div class="kpi-value">{report["total_products"]}</div></div>', unsafe_allow_html=True,
)
kpi_cols[1].markdown(
    f'<div class="kpi-card"><div class="kpi-label">Total Units</div>'
    f'<div class="kpi-value">{report["total_units"]:,}</div></div>', unsafe_allow_html=True,
)
kpi_cols[2].markdown(
    f'<div class="kpi-card"><div class="kpi-label">Inventory Value</div>'
    f'<div class="kpi-value">${report["total_inventory_value_cents"] / 100:,.2f}</div></div>', unsafe_allow_html=True,
)
kpi_cols[3].markdown(
    f'<div class="kpi-card"><div class="kpi-label">Low Stock Items</div>'
    f'<div class="kpi-value" style="color:{COLOR_DANGER if report["low_stock_count"] else COLOR_SUCCESS} !important">'
    f'{report["low_stock_count"]}</div></div>', unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)
tab_products, tab_orders, tab_reports = st.tabs(["📋 Products", "🧾 Purchase Orders", "📊 Reports"])

# ---------------------------------------------------------------------------
# Tab 1: Products — master-detail
# ---------------------------------------------------------------------------
with tab_products:
    products, err = _api_get("/products")
    if err:
        st.error(f"❌ {err}")
    elif not products:
        st.info("No products yet. Run `python scripts/seed_data.py` to load demo data.")
    else:
        left, right = st.columns([2, 1])

        with left:
            search = st.text_input("🔎 Search by name or SKU")
            show_low_stock_only = st.checkbox("Show low-stock only")

            filtered = products
            if search:
                filtered = [p for p in filtered if search.lower() in p["name"].lower() or search.lower() in p["sku"].lower()]
            if show_low_stock_only:
                filtered = [p for p in filtered if p["is_low_stock"]]

            if not filtered:
                st.info("No products match this filter.")
            else:

                df = pd.DataFrame(
                    [
                        {
                            "SKU": p["sku"], "Name": p["name"], "Qty": p["quantity_on_hand"],
                            "Price": f"${p['unit_price_cents'] / 100:.2f}",
                            "Status": "⚠️ Low Stock" if p["is_low_stock"] else "✅ OK",
                        }
                        for p in filtered
                    ]
                )
                st.dataframe(df, use_container_width=True, hide_index=True)
                selected_sku = st.selectbox("Select a product to manage", [p["sku"] for p in filtered])
                selected_product = next(p for p in filtered if p["sku"] == selected_sku)

        with right:
            st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
            st.markdown(f"### {selected_product['name']}")
            st.caption(f"SKU: {selected_product['sku']}")
            badge_class = "stock-low" if selected_product["is_low_stock"] else "stock-ok"
            badge_text = "LOW STOCK" if selected_product["is_low_stock"] else "IN STOCK"
            st.markdown(f'<span class="stock-badge {badge_class}">{badge_text}</span>', unsafe_allow_html=True)
            st.markdown(f"**On hand:** {selected_product['quantity_on_hand']} units")
            st.markdown(f"**Unit price:** ${selected_product['unit_price_cents'] / 100:.2f}")
            st.markdown(f"**Low-stock threshold:** {selected_product['low_stock_threshold']}")

            st.markdown("---")
            st.markdown("**Adjust Stock**")
            delta = st.number_input("Quantity change (+ to add, − to remove)", value=0, step=1, key=f"delta_{selected_product['product_id']}")
            if st.button("Apply Adjustment"):
                result, adj_err = _api_post(f"/products/{selected_product['product_id']}/adjust-stock", {"delta": delta})
                if adj_err:
                    st.error(f"❌ {adj_err}")
                else:
                    st.success(f"Updated — now {result['quantity_on_hand']} on hand.")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab 2: Purchase Orders
# ---------------------------------------------------------------------------
with tab_orders:
    st.markdown("### Reorder Suggestions")
    st.caption("Auto-generated from every product currently at or below its low-stock threshold.")
    suggestions, sugg_err = _api_get("/purchase-orders/reorder-suggestions", reorder_quantity=50)
    if sugg_err:
        st.error(f"❌ {sugg_err}")
    elif not suggestions:
        st.success("✅ No reorder suggestions — nothing is currently low on stock.")
    else:
        products_by_id = {p["product_id"]: p for p in (products or [])}
        for suggestion in suggestions:
            product = products_by_id.get(suggestion["product_id"], {})
            st.markdown(
                f"- **{product.get('name', suggestion['product_id'])}** ({product.get('sku', '')}) — "
                f"suggest ordering **{suggestion['quantity']}** units @ ${suggestion['unit_cost_cents'] / 100:.2f} each"
            )
        if st.button("📝 Create Purchase Order from Suggestions"):
            by_supplier: dict[int, list] = {}
            for suggestion in suggestions:
                product = products_by_id.get(suggestion["product_id"])
                if product:
                    by_supplier.setdefault(product["supplier_id"], []).append(suggestion)
            created_count = 0
            for supplier_id, lines in by_supplier.items():
                _, order_err = _api_post(
                    "/purchase-orders",
                    {"supplier_id": supplier_id, "lines": [
                        {"product_id": s["product_id"], "quantity": s["quantity"], "unit_cost_cents": s["unit_cost_cents"]}
                        for s in lines
                    ]},
                )
                if not order_err:
                    created_count += 1
            st.success(f"Created {created_count} purchase order(s) — one per supplier.")

# ---------------------------------------------------------------------------
# Tab 3: Reports
# ---------------------------------------------------------------------------
with tab_reports:
    st.markdown("### Inventory Health Snapshot")
    st.caption(f"Generated at {report['generated_at']}")
    if products:
        by_status = pd.DataFrame(
            [{"Status": "Low Stock" if p["is_low_stock"] else "Healthy"} for p in products]
        )
        st.bar_chart(by_status["Status"].value_counts())

    st.download_button(
        "⬇ Download Inventory Report (JSON)",
        str(report), file_name="inventory_report.json", mime="application/json",
    )

st.markdown(
    '<div class="footer">Inventory Management System · Day 38 of the 60-Day Python/AI Portfolio Challenge · '
    "Talks to a real FastAPI backend over HTTP — not a direct function call</div>",
    unsafe_allow_html=True,
)
