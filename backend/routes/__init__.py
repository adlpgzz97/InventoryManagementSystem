"""
Route handlers for Inventory Management System
"""

# Auth blueprint is now imported directly in app.py from simple_auth
from .dashboard import dashboard_bp
from .products import products_bp
from .stock import stock_bp
from .warehouses import warehouses_bp
from .scanner import scanner_bp
from .transactions import transactions_bp
from .bins import bins_bp

__all__ = ['dashboard_bp', 'products_bp', 'stock_bp', 'warehouses_bp', 'scanner_bp', 'transactions_bp', 'bins_bp']
