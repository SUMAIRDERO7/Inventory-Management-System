"""Central configuration for the Inventory Management System."""

from __future__ import annotations

# --- Database -------------------------------------------------------------
DATABASE_URL: str = "sqlite:///data/inventory.db"

# --- Business rules ---------------------------------------------------------
DEFAULT_LOW_STOCK_THRESHOLD: int = 10
DEFAULT_REORDER_QUANTITY: int = 50

# --- API ---------------------------------------------------------------------
API_HOST: str = "127.0.0.1"
API_PORT: int = 8000
API_BASE_URL: str = f"http://{API_HOST}:{API_PORT}"

# --- Brand palette (2026 Master Project Standard) -----------------------------
COLOR_PRIMARY: str = "#0A2540"
COLOR_SECONDARY: str = "#2563EB"
COLOR_ACCENT: str = "#38BDF8"
COLOR_SUCCESS: str = "#10B981"
COLOR_WARNING: str = "#F59E0B"
COLOR_DANGER: str = "#EF4444"
COLOR_BACKGROUND: str = "#F8FAFC"
COLOR_CARD: str = "#FFFFFF"
COLOR_TEXT_PRIMARY: str = "#111827"
COLOR_TEXT_SECONDARY: str = "#4B5563"
COLOR_BORDER: str = "#E2E8F0"
