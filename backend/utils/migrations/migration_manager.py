"""
Migration Manager for Inventory Management System
Handles the execution and tracking of database migrations
"""

import os
import importlib
import logging
from typing import List, Dict, Any, Optional, Type
from datetime import datetime

from backend.utils.database import get_db_cursor
from .migration_base import MigrationBase


class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, migrations_dir: str = None):
        self.migrations_dir = migrations_dir or os.path.join(
            os.path.dirname(__file__), 'versions'
        )
        self.logger = logging.getLogger(__name__)
        self.migrations_table = 'migrations'
        
        # Ensure migrations table exists
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Ensure the migrations tracking table exists"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(10) NOT NULL UNIQUE,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        checksum VARCHAR(64),
                        execution_time_ms INTEGER,
                        status VARCHAR(20) DEFAULT 'success'
                    )
                """)
        except Exception as e:
            self.logger.error(f"Failed to create migrations table: {e}")
            raise
    
    def get_migration_files(self) -> List[str]:
        """Get list of migration files from migrations directory"""
        try:
            if not os.path.exists(self.migrations_dir):
                self.logger.warning(f"Migrations directory does not exist: {self.migrations_dir}")
                return []
            
            migration_files = []
            for filename in os.listdir(self.migrations_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    migration_files.append(filename)
            
            return sorted(migration_files)
        except Exception as e:
            self.logger.error(f"Failed to get migration files: {e}")
            return []
    
    def load_migration_class(self, filename: str) -> Optional[Type[MigrationBase]]:
        """Load a migration class from a file"""
        try:
            # Remove .py extension
            module_name = filename[:-3]
            
            # Import the module
            module_path = f"backend.utils.migrations.versions.{module_name}"
            module = importlib.import_module(module_path)
            
            # Find the migration class (should be the only class that inherits from MigrationBase)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, MigrationBase) and 
                    attr != MigrationBase):
                    return attr
            
            self.logger.error(f"No migration class found in {filename}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load migration {filename}: {e}")
            return None
    
    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get list of already applied migrations"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(f"""
                    SELECT version, description, applied_at, status, execution_time_ms
                    FROM {self.migrations_table}
                    ORDER BY version
                """)
                results = cursor.fetchall()
                
                return [
                    {
                        'version': row[0],
                        'description': row[1],
                        'applied_at': row[2],
                        'status': row[3],
                        'execution_time_ms': row[4]
                    }
                    for row in results
                ]
        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """Get list of pending migrations"""
        try:
            applied_versions = {m['version'] for m in self.get_applied_migrations()}
            migration_files = self.get_migration_files()
            
            pending_migrations = []
            for filename in migration_files:
                migration_class = self.load_migration_class(filename)
                if migration_class:
                    migration = migration_class()
                    if migration.version not in applied_versions:
                        pending_migrations.append({
                            'filename': filename,
                            'version': migration.version,
                            'description': migration.description,
                            'class': migration_class
                        })
            
            return sorted(pending_migrations, key=lambda x: x['version'])
        except Exception as e:
            self.logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    def apply_migration(self, migration: MigrationBase) -> bool:
        """Apply a single migration"""
        start_time = datetime.now()
        
        try:
            # Validate migration
            if not migration.validate_migration():
                self.logger.error(f"Migration validation failed: {migration}")
                return False
            
            # Check dependencies
            dependencies = migration.get_dependencies()
            if dependencies:
                applied_versions = {m['version'] for m in self.get_applied_migrations()}
                missing_deps = [dep for dep in dependencies if dep not in applied_versions]
                if missing_deps:
                    self.logger.error(f"Missing dependencies for migration {migration.version}: {missing_deps}")
                    return False
            
            # Apply migration
            with get_db_cursor() as cursor:
                # Record migration start
                cursor.execute(f"""
                    INSERT INTO {self.migrations_table} 
                    (version, description, status) 
                    VALUES (%s, %s, 'running')
                """, (migration.version, migration.description))
                
                # Execute migration
                success = migration.up()
                
                if success:
                    # Update migration status to success
                    execution_time = (datetime.now() - start_time).microseconds // 1000
                    cursor.execute(f"""
                        UPDATE {self.migrations_table} 
                        SET status = 'success', execution_time_ms = %s
                        WHERE version = %s
                    """, (execution_time, migration.version))
                    
                    self.logger.info(f"Migration {migration.version} applied successfully in {execution_time}ms")
                    return True
                else:
                    # Update migration status to failed
                    cursor.execute(f"""
                        UPDATE {self.migrations_table} 
                        SET status = 'failed'
                        WHERE version = %s
                    """, (migration.version,))
                    
                    self.logger.error(f"Migration {migration.version} failed")
                    return False
                    
        except Exception as e:
            # Record migration failure
            try:
                with get_db_cursor() as cursor:
                    cursor.execute(f"""
                        UPDATE {self.migrations_table} 
                        SET status = 'failed'
                        WHERE version = %s
                    """, (migration.version,))
            except:
                pass
            
            self.logger.error(f"Migration {migration.version} failed with exception: {e}")
            return False
    
    def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration"""
        try:
            # Check if migration was applied
            applied_migrations = self.get_applied_migrations()
            migration_info = next((m for m in applied_migrations if m['version'] == version), None)
            
            if not migration_info:
                self.logger.error(f"Migration {version} was not applied")
                return False
            
            # Load migration class
            migration_files = self.get_migration_files()
            migration_class = None
            
            for filename in migration_files:
                temp_class = self.load_migration_class(filename)
                if temp_class:
                    temp_migration = temp_class()
                    if temp_migration.version == version:
                        migration_class = temp_class
                        break
            
            if not migration_class:
                self.logger.error(f"Migration class for version {version} not found")
                return False
            
            migration = migration_class()
            
            # Execute rollback
            with get_db_cursor() as cursor:
                success = migration.down()
                
                if success:
                    # Remove migration record
                    cursor.execute(f"""
                        DELETE FROM {self.migrations_table} 
                        WHERE version = %s
                    """, (version,))
                    
                    self.logger.info(f"Migration {version} rolled back successfully")
                    return True
                else:
                    self.logger.error(f"Migration {version} rollback failed")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Migration {version} rollback failed with exception: {e}")
            return False
    
    def migrate(self, target_version: str = None) -> bool:
        """Apply all pending migrations up to target version"""
        try:
            pending_migrations = self.get_pending_migrations()
            
            if not pending_migrations:
                self.logger.info("No pending migrations")
                return True
            
            self.logger.info(f"Found {len(pending_migrations)} pending migrations")
            
            for migration_info in pending_migrations:
                version = migration_info['version']
                
                # Check if we've reached the target version
                if target_version and version > target_version:
                    break
                
                self.logger.info(f"Applying migration {version}: {migration_info['description']}")
                
                migration = migration_info['class']()
                if not self.apply_migration(migration):
                    self.logger.error(f"Failed to apply migration {version}")
                    return False
            
            self.logger.info("All migrations applied successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Migration process failed: {e}")
            return False
    
    def rollback_all(self) -> bool:
        """Rollback all applied migrations"""
        try:
            applied_migrations = self.get_applied_migrations()
            
            if not applied_migrations:
                self.logger.info("No migrations to rollback")
                return True
            
            self.logger.info(f"Rolling back {len(applied_migrations)} migrations")
            
            # Rollback in reverse order
            for migration_info in reversed(applied_migrations):
                version = migration_info['version']
                self.logger.info(f"Rolling back migration {version}: {migration_info['description']}")
                
                if not self.rollback_migration(version):
                    self.logger.error(f"Failed to rollback migration {version}")
                    return False
            
            self.logger.info("All migrations rolled back successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback process failed: {e}")
            return False
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        try:
            applied_migrations = self.get_applied_migrations()
            pending_migrations = self.get_pending_migrations()
            
            return {
                'applied_count': len(applied_migrations),
                'pending_count': len(pending_migrations),
                'total_count': len(applied_migrations) + len(pending_migrations),
                'applied_migrations': applied_migrations,
                'pending_migrations': pending_migrations,
                'last_applied': applied_migrations[-1] if applied_migrations else None,
                'next_pending': pending_migrations[0] if pending_migrations else None
            }
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return {}
    
    def create_migration(self, version: str, description: str, migration_type: str = 'schema') -> str:
        """Create a new migration file"""
        try:
            if not os.path.exists(self.migrations_dir):
                os.makedirs(self.migrations_dir)
            
            # Create __init__.py if it doesn't exist
            init_file = os.path.join(self.migrations_dir, '__init__.py')
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write('"""Migration versions package"""\n')
            
            # Create migration file
            filename = f"{version}_{description.lower().replace(' ', '_')}.py"
            filepath = os.path.join(self.migrations_dir, filename)
            
            if os.path.exists(filepath):
                self.logger.warning(f"Migration file already exists: {filepath}")
                return filepath
            
            # Generate migration template
            if migration_type == 'schema':
                template = self._get_schema_migration_template(version, description)
            elif migration_type == 'data':
                template = self._get_data_migration_template(version, description)
            else:
                template = self._get_basic_migration_template(version, description)
            
            with open(filepath, 'w') as f:
                f.write(template)
            
            self.logger.info(f"Created migration file: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to create migration file: {e}")
            raise
    
    def _get_schema_migration_template(self, version: str, description: str) -> str:
        """Get template for schema migration"""
        return f'''"""
Migration {version}: {description}
Schema migration for Inventory Management System
"""

from backend.utils.migrations.migration_base import SchemaMigration


class Migration{version}(SchemaMigration):
    """{description}"""
    
    def get_version(self) -> str:
        return "{version}"
    
    def get_description(self) -> str:
        return "{description}"
    
    def up(self) -> bool:
        """Apply the migration"""
        try:
            # TODO: Implement schema changes
            # Example:
            # sql_statements = [
            #     self.create_table("new_table", [
            #         {{"name": "id", "type": "SERIAL", "primary_key": True}},
            #         {{"name": "name", "type": "VARCHAR(255)", "not_null": True}},
            #         {{"name": "created_at", "type": "TIMESTAMP", "default": "CURRENT_TIMESTAMP"}}
            #     ]),
            #     self.add_column("existing_table", "new_column", "VARCHAR(100)"),
            #     self.create_index("idx_existing_table_new_column", "existing_table", ["new_column"])
            # ]
            # 
            # with self.get_cursor() as cursor:
            #     return self.execute_sql(sql_statements, cursor)
            
            return True
        except Exception as e:
            self.logger.error(f"Migration failed: {{e}}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        try:
            # TODO: Implement rollback logic
            # Example:
            # rollback_sql = self.get_rollback_sql()
            # with self.get_cursor() as cursor:
            #     return self.execute_sql(rollback_sql, cursor)
            
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {{e}}")
            return False
'''
    
    def _get_data_migration_template(self, version: str, description: str) -> str:
        """Get template for data migration"""
        return f'''"""
Migration {version}: {description}
Data migration for Inventory Management System
"""

from backend.utils.migrations.migration_base import DataMigration


class Migration{version}(DataMigration):
    """{description}"""
    
    def get_version(self) -> str:
        return "{version}"
    
    def get_description(self) -> str:
        return "{description}"
    
    def up(self) -> bool:
        """Apply the migration"""
        try:
            # TODO: Implement data changes
            # Example:
            # data = [
            #     {{"name": "Sample Product", "sku": "SAMPLE-001", "description": "A sample product"}},
            #     {{"name": "Another Product", "sku": "SAMPLE-002", "description": "Another sample product"}}
            # ]
            # 
            # sql_statements = self.insert_data("products", data)
            # with self.get_cursor() as cursor:
            #     return self.execute_sql(sql_statements, cursor)
            
            return True
        except Exception as e:
            self.logger.error(f"Migration failed: {{e}}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        try:
            # TODO: Implement rollback logic
            # Example:
            # rollback_sql = self.get_rollback_sql()
            # with self.get_cursor() as cursor:
            #     return self.execute_sql(rollback_sql, cursor)
            
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {{e}}")
            return False
'''
    
    def _get_basic_migration_template(self, version: str, description: str) -> str:
        """Get template for basic migration"""
        return f'''"""
Migration {version}: {description}
Basic migration for Inventory Management System
"""

from backend.utils.migrations.migration_base import MigrationBase


class Migration{version}(MigrationBase):
    """{description}"""
    
    def get_version(self) -> str:
        return "{version}"
    
    def get_description(self) -> str:
        return "{description}"
    
    def up(self) -> bool:
        """Apply the migration"""
        try:
            # TODO: Implement migration logic
            return True
        except Exception as e:
            self.logger.error(f"Migration failed: {{e}}")
            return False
    
    def down(self) -> bool:
        """Rollback the migration"""
        try:
            # TODO: Implement rollback logic
            return True
        except Exception as e:
            self.logger.error(f"Rollback failed: {{e}}")
            return False
'''
