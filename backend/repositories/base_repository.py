"""
Base Repository Class for Inventory Management System
Provides common data access patterns and query building capabilities
"""

import logging
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic
from abc import ABC, abstractmethod
from contextlib import contextmanager

from backend.utils.database import get_db_cursor
from backend.exceptions import DatabaseError, NotFoundError
from backend.models.base_model import BaseModel

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseRepository(ABC, Generic[T]):
    """Base repository class with common data access patterns"""
    
    def __init__(self, model_class: Type[T], table_name: str):
        self.model_class = model_class
        self.table_name = table_name
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with automatic cleanup"""
        try:
            with get_db_cursor() as cursor:
                yield cursor
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
    
    def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    f"SELECT * FROM {self.table_name} WHERE id = %s",
                    (id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return self.model_class.from_dict(self._row_to_dict(cursor, result))
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get {self.table_name} by ID: {e}")
            raise DatabaseError(f"Failed to get {self.table_name} by ID: {str(e)}")
    
    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        """Convert cursor row to dictionary using column names"""
        if not cursor.description:
            return {}
        return dict(zip([col[0] for col in cursor.description], row))
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """Get all entities with optional pagination"""
        try:
            query = f"SELECT * FROM {self.table_name}"
            params = []
            
            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)
            
            if offset is not None:
                query += " OFFSET %s"
                params.append(offset)
            
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                return [self.model_class.from_dict(self._row_to_dict(cursor, row)) for row in results]
                
        except Exception as e:
            self.logger.error(f"Failed to get all {self.table_name}: {e}")
            raise DatabaseError(f"Failed to get all {self.table_name}: {str(e)}")
    
    def create(self, data: Dict[str, Any]) -> T:
        """Create new entity"""
        try:
            # Remove ID if present (will be auto-generated)
            data.pop('id', None)
            
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            
            query = f"""
                INSERT INTO {self.table_name} ({column_names})
                VALUES ({placeholders})
                RETURNING *
            """
            
            with self.get_cursor() as cursor:
                cursor.execute(query, list(data.values()))
                result = cursor.fetchone()
                
                return self.model_class.from_dict(self._row_to_dict(cursor, result))
                
        except Exception as e:
            self.logger.error(f"Failed to create {self.table_name}: {e}")
            raise DatabaseError(f"Failed to create {self.table_name}: {str(e)}")
    
    def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update existing entity"""
        try:
            # Remove ID and created_at from update data
            data.pop('id', None)
            data.pop('created_at', None)
            
            if not data:
                return self.get_by_id(id)
            
            set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
            query = f"""
                UPDATE {self.table_name}
                SET {set_clause}, updated_at = NOW()
                WHERE id = %s
                RETURNING *
            """
            
            params = list(data.values()) + [id]
            
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                if result:
                    return self.model_class.from_dict(self._row_to_dict(cursor, result))
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to update {self.table_name}: {e}")
            raise DatabaseError(f"Failed to update {self.table_name}: {str(e)}")
    
    def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {self.table_name} WHERE id = %s",
                    (id,)
                )
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to delete {self.table_name}: {e}")
            raise DatabaseError(f"Failed to delete {self.table_name}: {str(e)}")
    
    def count(self) -> int:
        """Get total count of entities"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            self.logger.error(f"Failed to count {self.table_name}: {e}")
            raise DatabaseError(f"Failed to count {self.table_name}: {str(e)}")
    
    def exists(self, id: str) -> bool:
        """Check if entity exists"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    f"SELECT 1 FROM {self.table_name} WHERE id = %s",
                    (id,)
                )
                result = cursor.fetchone()
                return result is not None
                
        except Exception as e:
            self.logger.error(f"Failed to check existence of {self.table_name}: {e}")
            raise DatabaseError(f"Failed to check existence of {self.table_name}: {str(e)}")
    
    def find_by(self, **kwargs) -> List[T]:
        """Find entities by multiple criteria"""
        try:
            if not kwargs:
                return self.get_all()
            
            conditions = []
            params = []
            
            for key, value in kwargs.items():
                if value is not None:
                    conditions.append(f"{key} = %s")
                    params.append(value)
            
            if not conditions:
                return self.get_all()
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"
            
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                return [self.model_class.from_dict(self._row_to_dict(cursor, row)) for row in results]
                
        except Exception as e:
            self.logger.error(f"Failed to find {self.table_name} by criteria: {e}")
            raise DatabaseError(f"Failed to find {self.table_name} by criteria: {str(e)}")
    
    def find_one_by(self, **kwargs) -> Optional[T]:
        """Find single entity by criteria"""
        results = self.find_by(**kwargs)
        return results[0] if results else None
    
    def execute_custom_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute custom SQL query"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                
                return [self._row_to_dict(cursor, row) for row in results]
                
        except Exception as e:
            self.logger.error(f"Failed to execute custom query: {e}")
            raise DatabaseError(f"Failed to execute custom query: {str(e)}")
    
    def execute_custom_query_single(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Execute custom SQL query returning single result"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params or ())
                result = cursor.fetchone()
                
                return self._row_to_dict(cursor, result) if result else None
                
        except Exception as e:
            self.logger.error(f"Failed to execute custom query: {e}")
            raise DatabaseError(f"Failed to execute custom query: {str(e)}")
    
    def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """Create multiple entities in bulk"""
        try:
            if not data_list:
                return []
            
            # Remove IDs from all items
            for data in data_list:
                data.pop('id', None)
            
            # All items should have the same structure
            columns = list(data_list[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            
            query = f"""
                INSERT INTO {self.table_name} ({column_names})
                VALUES ({placeholders})
                RETURNING *
            """
            
            created_entities = []
            
            with self.get_cursor() as cursor:
                for data in data_list:
                    cursor.execute(query, list(data.values()))
                    result = cursor.fetchone()
                    created_entities.append(self.model_class.from_dict(self._row_to_dict(cursor, result)))
            
            return created_entities
            
        except Exception as e:
            self.logger.error(f"Failed to bulk create {self.table_name}: {e}")
            raise DatabaseError(f"Failed to bulk create {self.table_name}: {str(e)}")
    
    def bulk_update(self, updates: List[Dict[str, Any]]) -> List[T]:
        """Update multiple entities in bulk"""
        try:
            if not updates:
                return []
            
            updated_entities = []
            
            with self.get_cursor() as cursor:
                for update_data in updates:
                    id_value = update_data.pop('id', None)
                    if id_value:
                        entity = self.update(id_value, update_data)
                        if entity:
                            updated_entities.append(entity)
            
            return updated_entities
            
        except Exception as e:
            self.logger.error(f"Failed to bulk update {self.table_name}: {e}")
            raise DatabaseError(f"Failed to bulk update {self.table_name}: {str(e)}")
    
    def bulk_delete(self, ids: List[str]) -> int:
        """Delete multiple entities in bulk"""
        try:
            if not ids:
                return 0
            
            placeholders = ', '.join(['%s'] * len(ids))
            query = f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})"
            
            with self.get_cursor() as cursor:
                cursor.execute(query, ids)
                return cursor.rowcount
                
        except Exception as e:
            self.logger.error(f"Failed to bulk delete {self.table_name}: {e}")
            raise DatabaseError(f"Failed to bulk delete {self.table_name}: {str(e)}")
