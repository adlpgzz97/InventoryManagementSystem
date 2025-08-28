"""
Route handlers for Inventory Management System
"""

from .auth import auth_bp
from .dashboard import dashboard_bp
from .products import products_bp

__all__ = ['auth_bp', 'dashboard_bp', 'products_bp']
