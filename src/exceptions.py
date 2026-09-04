"""Custom exception hierarchy for the Inventory Management System."""

from __future__ import annotations


class InventoryError(Exception):
    """Base exception for all errors raised by this project."""


class ProductNotFoundError(InventoryError):
    """Raised when a referenced product ID doesn't exist."""


class SupplierNotFoundError(InventoryError):
    """Raised when a referenced supplier ID doesn't exist."""


class CategoryNotFoundError(InventoryError):
    """Raised when a referenced category ID doesn't exist."""


class PurchaseOrderNotFoundError(InventoryError):
    """Raised when a referenced purchase order ID doesn't exist."""


class InvalidQuantityError(InventoryError):
    """Raised when a quantity would be negative or is otherwise invalid."""


class DuplicateSKUError(InventoryError):
    """Raised when creating a product with a SKU that already exists."""


class InsufficientStockError(InventoryError):
    """Raised when attempting to remove more stock than is on hand."""
