"""
Dashboard Service for Inventory Management System
Handles all business logic for dashboard operations
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from .base_service import BaseService, ServiceError, ValidationError
from backend.utils.database import get_db_connection


class DashboardService(BaseService):
    """Service for dashboard business logic"""
    
    def __init__(self):
        super().__init__()
    
    def get_service_name(self) -> str:
        return "DashboardService"
    
    def get_dashboard_data(self, user_id: str = None) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            self.log_operation("get_dashboard_data", {"user_id": user_id})
            
            dashboard_data = {
                "stats": self._get_dashboard_stats(),
                "alerts": self._get_dashboard_alerts(),
                "recent_activity": self._get_recent_activity(),
                "quick_actions": self._get_quick_actions(user_id)
            }
            
            self.log_operation("get_dashboard_data_success", {"data_keys": list(dashboard_data.keys())})
            return dashboard_data
            
        except Exception as e:
            self.log_error("get_dashboard_data", e, {"user_id": user_id})
            raise ServiceError(f"Failed to get dashboard data: {str(e)}")
    
    def _get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get total products count
                    cursor.execute("SELECT COUNT(*) FROM products")
                    total_products = cursor.fetchone()[0]
                    
                    # Get total stock items count
                    cursor.execute("SELECT COUNT(*) FROM stock_items")
                    total_stock_items = cursor.fetchone()[0]
                    
                    # Get low stock count (less than 10 items)
                    cursor.execute("SELECT COUNT(*) FROM stock_items WHERE on_hand < 10")
                    low_stock_count = cursor.fetchone()[0]
                    
                    # Get out of stock count
                    cursor.execute("SELECT COUNT(*) FROM stock_items WHERE on_hand = 0")
                    out_of_stock_count = cursor.fetchone()[0]
                    
                    # Get total warehouses count
                    cursor.execute("SELECT COUNT(*) FROM warehouses")
                    total_warehouses = cursor.fetchone()[0]
                    
                    return {
                        "total_products": total_products,
                        "total_stock_items": total_stock_items,
                        "low_stock_count": low_stock_count,
                        "out_of_stock_count": out_of_stock_count,
                        "total_warehouses": total_warehouses
                    }
                    
        except Exception as e:
            self.handle_database_error("get_dashboard_stats", e)
            return {}
    
    def _get_dashboard_alerts(self) -> List[Dict[str, Any]]:
        """Get dashboard alerts and notifications"""
        alerts = []
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Check for low stock items
                    cursor.execute("""
                        SELECT p.name, si.on_hand, si.bin_id
                        FROM stock_items si
                        JOIN products p ON si.product_id = p.id
                        WHERE si.on_hand < 10 AND si.on_hand > 0
                        ORDER BY si.on_hand ASC
                        LIMIT 5
                    """)
                    
                    low_stock_items = cursor.fetchall()
                    for item in low_stock_items:
                        alerts.append({
                            "type": "warning",
                            "message": f"Low stock: {item[0]} (Quantity: {item[1]})",
                            "details": f"Bin: {item[2]}",
                            "priority": "medium"
                        })
                    
                    # Check for out of stock items
                    cursor.execute("""
                        SELECT p.name, si.bin_id
                        FROM stock_items si
                        JOIN products p ON si.product_id = p.id
                        WHERE si.on_hand = 0
                        LIMIT 5
                    """)
                    
                    out_of_stock_items = cursor.fetchall()
                    for item in out_of_stock_items:
                        alerts.append({
                            "type": "error",
                            "message": f"Out of stock: {item[0]}",
                            "details": f"Bin: {item[1]}",
                            "priority": "high"
                        })
                    
        except Exception as e:
            self.handle_database_error("get_dashboard_alerts", e)
        
        return alerts
    
    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent system activity"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get recent stock movements (simplified - you might have a separate activity table)
                    cursor.execute("""
                        SELECT p.name, si.on_hand, si.created_at
                        FROM stock_items si
                        JOIN products p ON si.product_id = p.id
                        ORDER BY si.created_at DESC
                        LIMIT 10
                    """)
                    
                    recent_activity = []
                    for row in cursor.fetchall():
                        recent_activity.append({
                            "type": "stock_update",
                            "description": f"Stock updated for {row[0]}",
                            "quantity": row[1],
                            "timestamp": row[2].isoformat() if row[2] else None
                        })
                    
                    return recent_activity
                    
        except Exception as e:
            self.handle_database_error("get_recent_activity", e)
            return []
    
    def _get_quick_actions(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get available quick actions based on user role"""
        quick_actions = [
            {
                "id": "add_product",
                "name": "Add Product",
                "description": "Create a new product",
                "url": "/products/add",
                "icon": "plus-circle",
                "requires_auth": True
            },
            {
                "id": "view_stock",
                "name": "View Stock",
                "description": "Check current stock levels",
                "url": "/stock",
                "icon": "box",
                "requires_auth": False
            },
            {
                "id": "scan_barcode",
                "name": "Scan Barcode",
                "description": "Scan product barcode",
                "url": "/scanner",
                "icon": "upc-scan",
                "requires_auth": True
            }
        ]
        
        # Add role-specific actions if user_id is provided
        if user_id:
            # You could add role-based actions here
            quick_actions.append({
                "id": "export_data",
                "name": "Export Data",
                "description": "Export inventory data",
                "url": "/export",
                "icon": "download",
                "requires_auth": True
            })
        
        return quick_actions
    
    def get_user_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Get personalized dashboard data for a specific user"""
        try:
            self.validate_required_fields({"user_id": user_id}, ["user_id"])
            
            dashboard_data = self.get_dashboard_data(user_id)
            
            # Add user-specific data
            user_data = self._get_user_specific_data(user_id)
            dashboard_data.update(user_data)
            
            return dashboard_data
            
        except Exception as e:
            self.log_error("get_user_dashboard_data", e, {"user_id": user_id})
            raise ServiceError(f"Failed to get user dashboard data: {str(e)}")
    
    def _get_user_specific_data(self, user_id: str) -> Dict[str, Any]:
        """Get data specific to a user (recent actions, preferences, etc.)"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get user's recent actions (if you have an activity log table)
                    # For now, return basic user info
                    cursor.execute("SELECT username, role FROM users WHERE id = %s", (user_id,))
                    user_info = cursor.fetchone()
                    
                    if user_info:
                        return {
                            "user_info": {
                                "username": user_info[0],
                                "role": user_info[1]
                            },
                            "personalized_alerts": self._get_personalized_alerts(user_id)
                        }
                    else:
                        return {"user_info": None, "personalized_alerts": []}
                        
        except Exception as e:
            self.handle_database_error("get_user_specific_data", e)
            return {"user_info": None, "personalized_alerts": []}
    
    def _get_personalized_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get alerts personalized for a specific user"""
        # This could include alerts based on user role, assigned warehouses, etc.
        # For now, return empty list
        return []
