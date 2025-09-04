"""
Base Migration Class for Inventory Management System
Provides the foundation for all database migrations
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging


class MigrationBase(ABC):
    """Base class for all database migrations"""
    
    def __init__(self):
        self.version = self.get_version()
        self.description = self.get_description()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_version(self) -> str:
        """Return the migration version (e.g., '001', '002')"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what this migration does"""
        pass
    
    @abstractmethod
    def up(self) -> bool:
        """Apply the migration (forward migration)"""
        pass
    
    @abstractmethod
    def down(self) -> bool:
        """Rollback the migration (reverse migration)"""
        pass
    
    def get_dependencies(self) -> List[str]:
        """Return list of migration versions this migration depends on"""
        return []
    
    def get_rollback_sql(self) -> List[str]:
        """Return list of SQL statements to rollback this migration"""
        return []
    
    def get_forward_sql(self) -> List[str]:
        """Return list of SQL statements to apply this migration"""
        return []
    
    def execute_sql(self, sql_statements: List[str], cursor) -> bool:
        """Execute a list of SQL statements"""
        try:
            for sql in sql_statements:
                if sql.strip():
                    cursor.execute(sql)
                    self.logger.debug(f"Executed SQL: {sql}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to execute SQL: {e}")
            return False
    
    def validate_migration(self) -> bool:
        """Validate that the migration can be applied"""
        try:
            # Check if version is valid
            if not self.version or not self.version.isdigit():
                self.logger.error(f"Invalid migration version: {self.version}")
                return False
            
            # Check if description is provided
            if not self.description:
                self.logger.error("Migration description is required")
                return False
            
            # Check if up and down methods are implemented
            if not hasattr(self, 'up') or not hasattr(self, 'down'):
                self.logger.error("Migration must implement up() and down() methods")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Migration validation failed: {e}")
            return False
    
    def __str__(self) -> str:
        return f"Migration {self.version}: {self.description}"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} version='{self.version}' description='{self.description}'>"


class SchemaMigration(MigrationBase):
    """Base class for schema-related migrations"""
    
    def __init__(self):
        super().__init__()
        self.tables_created = []
        self.tables_dropped = []
        self.columns_added = []
        self.columns_modified = []
        self.columns_dropped = []
        self.indexes_created = []
        self.indexes_dropped = []
        self.constraints_added = []
        self.constraints_dropped = []
    
    def create_table(self, table_name: str, columns: List[Dict[str, Any]]) -> str:
        """Generate CREATE TABLE SQL"""
        column_definitions = []
        for column in columns:
            col_def = f"{column['name']} {column['type']}"
            
            if column.get('not_null'):
                col_def += " NOT NULL"
            
            if column.get('default') is not None:
                col_def += f" DEFAULT {column['default']}"
            
            if column.get('primary_key'):
                col_def += " PRIMARY KEY"
            
            column_definitions.append(col_def)
        
        sql = f"CREATE TABLE {table_name} (\n"
        sql += ",\n".join(f"    {col}" for col in column_definitions)
        sql += "\n)"
        
        self.tables_created.append(table_name)
        return sql
    
    def drop_table(self, table_name: str) -> str:
        """Generate DROP TABLE SQL"""
        self.tables_dropped.append(table_name)
        return f"DROP TABLE IF EXISTS {table_name} CASCADE"
    
    def add_column(self, table_name: str, column_name: str, column_type: str, 
                   not_null: bool = False, default: Any = None) -> str:
        """Generate ADD COLUMN SQL"""
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        
        if not_null:
            sql += " NOT NULL"
        
        if default is not None:
            sql += f" DEFAULT {default}"
        
        self.columns_added.append(f"{table_name}.{column_name}")
        return sql
    
    def drop_column(self, table_name: str, column_name: str) -> str:
        """Generate DROP COLUMN SQL"""
        self.columns_dropped.append(f"{table_name}.{column_name}")
        return f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
    
    def create_index(self, index_name: str, table_name: str, columns: List[str], 
                    unique: bool = False) -> str:
        """Generate CREATE INDEX SQL"""
        unique_clause = "UNIQUE " if unique else ""
        columns_str = ", ".join(columns)
        sql = f"CREATE {unique_clause}INDEX {index_name} ON {table_name} ({columns_str})"
        
        self.indexes_created.append(index_name)
        return sql
    
    def drop_index(self, index_name: str) -> str:
        """Generate DROP INDEX SQL"""
        self.indexes_dropped.append(index_name)
        return f"DROP INDEX IF EXISTS {index_name}"
    
    def add_foreign_key(self, table_name: str, column_name: str, 
                       reference_table: str, reference_column: str,
                       constraint_name: str = None) -> str:
        """Generate ADD FOREIGN KEY SQL"""
        if not constraint_name:
            constraint_name = f"fk_{table_name}_{column_name}"
        
        sql = f"""
        ALTER TABLE {table_name} 
        ADD CONSTRAINT {constraint_name} 
        FOREIGN KEY ({column_name}) 
        REFERENCES {reference_table}({reference_column})
        """
        
        self.constraints_added.append(constraint_name)
        return sql
    
    def drop_foreign_key(self, table_name: str, constraint_name: str) -> str:
        """Generate DROP FOREIGN KEY SQL"""
        self.constraints_dropped.append(constraint_name)
        return f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}"
    
    def get_rollback_sql(self) -> List[str]:
        """Generate rollback SQL for schema changes"""
        rollback_sql = []
        
        # Drop added constraints
        for constraint in self.constraints_added:
            rollback_sql.append(f"ALTER TABLE {constraint.split('_')[1]} DROP CONSTRAINT {constraint}")
        
        # Drop added indexes
        for index in self.indexes_created:
            rollback_sql.append(f"DROP INDEX IF EXISTS {index}")
        
        # Drop added columns
        for column in self.columns_added:
            table_name, column_name = column.split('.')
            rollback_sql.append(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")
        
        # Recreate dropped tables
        for table in self.tables_dropped:
            rollback_sql.append(f"-- Recreate table {table} (manual intervention required)")
        
        # Drop created tables
        for table in self.tables_created:
            rollback_sql.append(f"DROP TABLE IF EXISTS {table} CASCADE")
        
        return rollback_sql


class DataMigration(MigrationBase):
    """Base class for data-related migrations"""
    
    def __init__(self):
        super().__init__()
        self.data_inserted = []
        self.data_updated = []
        self.data_deleted = []
    
    def insert_data(self, table_name: str, data: List[Dict[str, Any]]) -> List[str]:
        """Generate INSERT statements"""
        if not data:
            return []
        
        sql_statements = []
        columns = list(data[0].keys())
        
        for row in data:
            values = [str(row.get(col, 'NULL')) for col in columns]
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)})"
            sql_statements.append(sql)
            self.data_inserted.append(f"{table_name}: {len(values)} values")
        
        return sql_statements
    
    def update_data(self, table_name: str, set_values: Dict[str, Any], 
                   where_condition: str, where_params: List[Any] = None) -> str:
        """Generate UPDATE statement"""
        set_clause = ", ".join([f"{k} = {v}" for k, v in set_values.items()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_condition}"
        
        self.data_updated.append(f"{table_name}: {len(set_values)} fields")
        return sql
    
    def delete_data(self, table_name: str, where_condition: str, 
                   where_params: List[Any] = None) -> str:
        """Generate DELETE statement"""
        sql = f"DELETE FROM {table_name} WHERE {where_condition}"
        self.data_deleted.append(f"{table_name}: filtered by {where_condition}")
        return sql
    
    def get_rollback_sql(self) -> List[str]:
        """Generate rollback SQL for data changes"""
        rollback_sql = []
        
        # Note: Data rollbacks are complex and often require manual intervention
        # This provides a basic framework that can be extended
        
        for data_change in self.data_inserted:
            rollback_sql.append(f"-- Rollback data insertion: {data_change}")
        
        for data_change in self.data_updated:
            rollback_sql.append(f"-- Rollback data update: {data_change}")
        
        for data_change in self.data_deleted:
            rollback_sql.append(f"-- Rollback data deletion: {data_change}")
        
        return rollback_sql
