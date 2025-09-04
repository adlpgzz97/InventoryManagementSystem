"""
User Repository for Inventory Management System
Handles all user-related database operations
"""

from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from backend.models.user import User


class UserRepository(BaseRepository[User]):
    """Repository for user data access"""
    
    def __init__(self):
        super().__init__(User, 'users')
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.find_one_by(username=username)
    
    def get_by_role(self, role: str) -> List[User]:
        """Get users by role"""
        return self.find_by(role=role)
    
    def get_active_users(self) -> List[User]:
        """Get all active users (assuming there's an active field)"""
        # Note: This assumes users have an active field
        # If not, this method can be modified or removed
        return self.find_by(active=True)
    
    def get_users_by_warehouse(self, warehouse_id: str) -> List[Dict[str, Any]]:
        """Get users associated with a specific warehouse"""
        # Note: This assumes there's a user_warehouse relationship table
        # If not, this method can be modified or removed
        query = """
            SELECT u.*, uw.warehouse_id
            FROM users u
            INNER JOIN user_warehouses uw ON u.id = uw.user_id
            WHERE uw.warehouse_id = %s
            ORDER BY u.username
        """
        
        return self.execute_custom_query(query, (warehouse_id,))
    
    def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user activity summary based on transactions"""
        query = """
            SELECT u.username,
                   COUNT(st.id) as total_transactions,
                   COUNT(CASE WHEN st.transaction_type = 'receive' THEN 1 END) as receive_count,
                   COUNT(CASE WHEN st.transaction_type = 'ship' THEN 1 END) as ship_count,
                   COUNT(CASE WHEN st.transaction_type = 'adjust' THEN 1 END) as adjust_count,
                   COUNT(CASE WHEN st.transaction_type = 'transfer' THEN 1 END) as transfer_count,
                   COUNT(CASE WHEN st.transaction_type = 'reserve' THEN 1 END) as reserve_count,
                   COUNT(CASE WHEN st.transaction_type = 'release' THEN 1 END) as release_count,
                   MAX(st.created_at) as last_activity
            FROM users u
            LEFT JOIN stock_transactions st ON u.id = st.user_id
            WHERE u.id = %s 
              AND (st.created_at >= CURRENT_DATE - INTERVAL '%s days' OR st.created_at IS NULL)
            GROUP BY u.id, u.username
        """
        
        return self.execute_custom_query_single(query, (user_id, days)) or {}
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get overall user statistics"""
        query = """
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
                COUNT(CASE WHEN role = 'manager' THEN 1 END) as manager_users,
                COUNT(CASE WHEN role = 'worker' THEN 1 END) as worker_users
            FROM users
        """
        
        return self.execute_custom_query_single(query) or {}
    
    def search_users(self, search_term: str) -> List[User]:
        """Search users by username or role"""
        if not search_term:
            return self.get_all()
        
        query = """
            SELECT * FROM users 
            WHERE username ILIKE %s 
               OR role ILIKE %s
            ORDER BY username
        """
        
        search_pattern = f"%{search_term}%"
        params = (search_pattern, search_pattern)
        
        results = self.execute_custom_query(query, params)
        return [User.from_dict(result) for result in results]
    
    def get_users_with_recent_activity(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get users with recent activity"""
        query = """
            SELECT u.id, u.username, u.role,
                   COUNT(st.id) as recent_transactions,
                   MAX(st.created_at) as last_activity
            FROM users u
            LEFT JOIN stock_transactions st ON u.id = st.user_id
            WHERE st.created_at >= CURRENT_DATE - INTERVAL '%s days'
               OR st.created_at IS NULL
            GROUP BY u.id, u.username, u.role
            ORDER BY last_activity DESC NULLS LAST
        """
        
        return self.execute_custom_query(query, (days,))
    
    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get user permissions based on role"""
        query = """
            SELECT u.id, u.username, u.role,
                   CASE 
                       WHEN u.role = 'admin' THEN true 
                       ELSE false 
                   END as can_manage_users,
                   CASE 
                       WHEN u.role IN ('admin', 'manager') THEN true 
                       ELSE false 
                   END as can_manage_inventory,
                   CASE 
                       WHEN u.role IN ('admin', 'manager') THEN true 
                       ELSE false 
                   END as can_delete_items,
                   CASE 
                       WHEN u.role IN ('admin', 'manager') THEN true 
                       ELSE false 
                   END as can_export_data,
                   CASE 
                       WHEN u.role IN ('admin', 'manager') THEN true 
                       ELSE false 
                   END as can_view_reports
            FROM users u
            WHERE u.id = %s
        """
        
        return self.execute_custom_query_single(query, (user_id,)) or {}
    
    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """Update user role"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users 
                    SET role = %s 
                    WHERE id = %s
                    """,
                    (new_role, user_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to update user role: {e}")
            return False
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user (assuming there's an active field)"""
        # Note: This assumes users have an active field
        # If not, this method can be modified or removed
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users 
                    SET active = false 
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Failed to deactivate user: {e}")
            return False
    
    def get_user_login_history(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get user login history (assuming there's a login_logs table)"""
        # Note: This assumes there's a login_logs table
        # If not, this method can be modified or removed
        query = """
            SELECT ll.*
            FROM login_logs ll
            WHERE ll.user_id = %s
            ORDER BY ll.login_time DESC
        """
        
        params = [user_id]
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def get_users_by_activity_level(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get users grouped by activity level"""
        query = """
            SELECT 
                CASE 
                    WHEN transaction_count = 0 THEN 'Inactive'
                    WHEN transaction_count <= 10 THEN 'Low Activity'
                    WHEN transaction_count <= 50 THEN 'Medium Activity'
                    ELSE 'High Activity'
                END as activity_level,
                COUNT(*) as user_count,
                AVG(transaction_count) as avg_transactions
            FROM (
                SELECT u.id, u.username, u.role,
                       COUNT(st.id) as transaction_count
                FROM users u
                LEFT JOIN stock_transactions st ON u.id = st.user_id
                WHERE st.created_at >= CURRENT_DATE - INTERVAL '%s days'
                   OR st.created_at IS NULL
                GROUP BY u.id, u.username, u.role
            ) user_activity
            GROUP BY activity_level
            ORDER BY 
                CASE activity_level
                    WHEN 'High Activity' THEN 1
                    WHEN 'Medium Activity' THEN 2
                    WHEN 'Low Activity' THEN 3
                    WHEN 'Inactive' THEN 4
                END
        """
        
        return self.execute_custom_query(query, (days,))
