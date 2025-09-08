"""
Category Model for Inventory Management System
Handles product categories with proper database relationships
"""

from typing import List, Dict, Any, Optional
from backend.models.base_model import BaseModel
from backend.utils.database import execute_query
import logging

logger = logging.getLogger(__name__)

class Category(BaseModel):
    """Category model for product categorization"""
    
    def __init__(self, id: str = None, code: str = None, description: str = None, 
                 created_at: str = None, updated_at: str = None):
        self.id = id
        self.code = code
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def get_all(cls) -> List['Category']:
        """Get all categories ordered by code"""
        try:
            results = execute_query(
                "SELECT id, code, description, created_at, updated_at FROM categories ORDER BY code",
                fetch_all=True
            )
            return [cls.from_dict(result) for result in results] if results else []
        except Exception as e:
            logger.error(f"Error getting all categories: {e}")
            return []
    
    @classmethod
    def get_by_id(cls, category_id: str) -> Optional['Category']:
        """Get category by ID"""
        try:
            result = execute_query(
                "SELECT id, code, description, created_at, updated_at FROM categories WHERE id = %s",
                (category_id,),
                fetch_one=True
            )
            return cls.from_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting category by ID {category_id}: {e}")
            return None
    
    @classmethod
    def get_by_code(cls, code: str) -> Optional['Category']:
        """Get category by code"""
        try:
            result = execute_query(
                "SELECT id, code, description, created_at, updated_at FROM categories WHERE code = %s",
                (code,),
                fetch_one=True
            )
            return cls.from_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting category by code {code}: {e}")
            return None
    
    @classmethod
    def create(cls, code: str, description: str = None) -> Optional['Category']:
        """Create a new category"""
        try:
            result = execute_query(
                "INSERT INTO categories (code, description) VALUES (%s, %s) RETURNING id, code, description, created_at, updated_at",
                (code, description),
                fetch_one=True
            )
            return cls.from_dict(result) if result else None
        except Exception as e:
            logger.error(f"Error creating category {code}: {e}")
            return None
    
    def update(self, code: str = None, description: str = None) -> bool:
        """Update category"""
        try:
            if code is None and description is None:
                return False
            
            updates = []
            params = []
            
            if code is not None:
                updates.append("code = %s")
                params.append(code)
                self.code = code
            
            if description is not None:
                updates.append("description = %s")
                params.append(description)
                self.description = description
            
            updates.append("updated_at = now()")
            params.append(self.id)
            
            execute_query(
                f"UPDATE categories SET {', '.join(updates)} WHERE id = %s",
                params
            )
            return True
        except Exception as e:
            logger.error(f"Error updating category {self.id}: {e}")
            return False
    
    def delete(self) -> bool:
        """Delete category (will set product category_id to NULL due to ON DELETE SET NULL)"""
        try:
            execute_query("DELETE FROM categories WHERE id = %s", (self.id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting category {self.id}: {e}")
            return False
    
    @classmethod
    def get_products_count(cls) -> List[Dict[str, Any]]:
        """Get count of products per category"""
        try:
            results = execute_query(
                """
                SELECT 
                    c.id, c.code, c.description,
                    COUNT(p.id) as product_count
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id
                GROUP BY c.id, c.code, c.description
                ORDER BY c.code
                """,
                fetch_all=True
            )
            return results if results else []
        except Exception as e:
            logger.error(f"Error getting products count by category: {e}")
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert category to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """Create category from dictionary"""
        return cls(
            id=data.get('id'),
            code=data.get('code'),
            description=data.get('description'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def __str__(self):
        return f"Category({self.code}: {self.description})"
    
    def __repr__(self):
        return f"Category(id={self.id}, code={self.code}, description={self.description})"
