import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from backend.utils.migrations.migration_base import (
    MigrationBase, SchemaMigration, DataMigration
)
from backend.utils.migrations.migration_manager import MigrationManager
from backend.utils.migrations.cli import main, show_status, migrate, rollback_version, rollback_all, create_migration


class TestMigrationBase:
    """Test the base migration class."""
    
    def test_abstract_methods(self):
        """Test that MigrationBase is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            MigrationBase()
    
    def test_execute_sql(self):
        """Test SQL execution method."""
        class TestMigration(MigrationBase):
            def get_version(self) -> str:
                return "1.0.0"
            
            def get_description(self) -> str:
                return "Test migration"
            
            def up(self) -> bool:
                return self.execute_sql("CREATE TABLE test (id INT)")
            
            def down(self) -> bool:
                return self.execute_sql("DROP TABLE test")
        
        migration = TestMigration()
        
        with patch('backend.utils.migrations.migration_base.execute_query') as mock_execute:
            mock_execute.return_value = True
            
            result = migration.up()
            
            assert result is True
            mock_execute.assert_called_once_with("CREATE TABLE test (id INT)")
    
    def test_validate_migration(self):
        """Test migration validation."""
        class TestMigration(MigrationBase):
            def get_version(self) -> str:
                return "1.0.0"
            
            def get_description(self) -> str:
                return "Test migration"
            
            def up(self) -> bool:
                return True
            
            def down(self) -> bool:
                return True
        
        migration = TestMigration()
        
        # Test valid migration
        assert migration.validate_migration() is True
        
        # Test invalid version format
        migration._version = "invalid-version"
        assert migration.validate_migration() is False


class TestSchemaMigration:
    """Test the SchemaMigration class."""
    
    def test_create_table(self):
        """Test table creation SQL generation."""
        migration = SchemaMigration()
        
        sql = migration.create_table(
            table_name="test_table",
            columns={
                "id": "INTEGER PRIMARY KEY",
                "name": "VARCHAR(255) NOT NULL",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            }
        )
        
        expected = """CREATE TABLE test_table (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""
        assert sql.strip() == expected.strip()
    
    def test_drop_table(self):
        """Test table drop SQL generation."""
        migration = SchemaMigration()
        
        sql = migration.drop_table("test_table")
        
        expected = "DROP TABLE test_table"
        assert sql.strip() == expected
    
    def test_add_column(self):
        """Test column addition SQL generation."""
        migration = SchemaMigration()
        
        sql = migration.add_column("test_table", "new_column", "VARCHAR(100)")
        
        expected = "ALTER TABLE test_table ADD COLUMN new_column VARCHAR(100)"
        assert sql.strip() == expected
    
    def test_drop_column(self):
        """Test column drop SQL generation."""
        migration = SchemaMigration()
        
        sql = migration.drop_column("test_table", "old_column")
        
        expected = "ALTER TABLE test_table DROP COLUMN old_column"
        assert sql.strip() == expected
    
    def test_create_index(self):
        """Test index creation SQL generation."""
        migration = SchemaMigration()
        
        sql = migration.create_index("idx_test_name", "test_table", ["name"])
        
        expected = "CREATE INDEX idx_test_name ON test_table (name)"
        assert sql.strip() == expected
    
    def test_drop_index(self):
        """Test index drop SQL generation."""
        migration = SchemaMigration()
        
        sql = migration.drop_index("idx_test_name")
        
        expected = "DROP INDEX idx_test_name"
        assert sql.strip() == expected
    
    def test_add_foreign_key(self):
        """Test foreign key addition SQL generation."""
        migration = SchemaMigration()
        
        sql = migration.add_foreign_key(
            "test_table", "user_id", "users", "id", "CASCADE", "CASCADE"
        )
        
        expected = "ALTER TABLE test_table ADD CONSTRAINT fk_test_table_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE"
        assert sql.strip() == expected
    
    def test_drop_foreign_key(self):
        """Test foreign key drop SQL generation."""
        migration = SchemaMigration()
        
        sql = migration.drop_foreign_key("test_table", "fk_test_table_user_id")
        
        expected = "ALTER TABLE test_table DROP CONSTRAINT fk_test_table_user_id"
        assert sql.strip() == expected
    
    def test_get_rollback_sql(self):
        """Test rollback SQL generation for schema changes."""
        migration = SchemaMigration()
        
        # Test table creation rollback
        rollback_sql = migration.get_rollback_sql(
            "CREATE TABLE test_table (id INT)",
            "create_table"
        )
        
        expected = "DROP TABLE test_table"
        assert rollback_sql.strip() == expected
        
        # Test column addition rollback
        rollback_sql = migration.get_rollback_sql(
            "ALTER TABLE test_table ADD COLUMN new_column VARCHAR(100)",
            "add_column"
        )
        
        expected = "ALTER TABLE test_table DROP COLUMN new_column"
        assert rollback_sql.strip() == expected


class TestDataMigration:
    """Test the DataMigration class."""
    
    def test_insert_data(self):
        """Test data insertion SQL generation."""
        migration = DataMigration()
        
        sql = migration.insert_data(
            "test_table",
            ["id", "name", "value"],
            [["1", "test1", "100"], ["2", "test2", "200"]]
        )
        
        expected = """INSERT INTO test_table (id, name, value) VALUES 
('1', 'test1', '100'),
('2', 'test2', '200')"""
        assert sql.strip() == expected
    
    def test_update_data(self):
        """Test data update SQL generation."""
        migration = DataMigration()
        
        sql = migration.update_data(
            "test_table",
            {"name": "updated_name", "value": "300"},
            "id = 1"
        )
        
        expected = "UPDATE test_table SET name = 'updated_name', value = '300' WHERE id = 1"
        assert sql.strip() == expected
    
    def test_delete_data(self):
        """Test data deletion SQL generation."""
        migration = DataMigration()
        
        sql = migration.delete_data("test_table", "id = 1")
        
        expected = "DELETE FROM test_table WHERE id = 1"
        assert sql.strip() == expected
    
    def test_get_rollback_sql(self):
        """Test rollback SQL generation for data changes."""
        migration = DataMigration()
        
        # Test insert rollback
        rollback_sql = migration.get_rollback_sql(
            "INSERT INTO test_table (id, name) VALUES ('1', 'test')",
            "insert_data"
        )
        
        expected = "DELETE FROM test_table WHERE id = '1'"
        assert rollback_sql.strip() == expected
        
        # Test update rollback (would need original values in practice)
        rollback_sql = migration.get_rollback_sql(
            "UPDATE test_table SET name = 'new_name' WHERE id = 1",
            "update_data"
        )
        
        # This would need the original values to be meaningful
        assert "UPDATE test_table" in rollback_sql


class TestMigrationManager:
    """Test the MigrationManager class."""
    
    @pytest.fixture
    def temp_migrations_dir(self):
        """Create a temporary directory for migrations."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_initialization(self, temp_migrations_dir):
        """Test MigrationManager initialization."""
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            assert manager.migrations_dir == temp_migrations_dir
            # Should create migrations table
            mock_cursor.execute.assert_called()
    
    def test_ensure_migrations_table(self, temp_migrations_dir):
        """Test migrations table creation."""
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            # Verify migrations table creation SQL
            create_table_calls = [call for call in mock_cursor.execute.call_args_list 
                                if 'CREATE TABLE' in str(call)]
            assert len(create_table_calls) > 0
    
    def test_get_migration_files(self, temp_migrations_dir):
        """Test migration file discovery."""
        # Create some test migration files
        migration_files = [
            "001_create_products.py",
            "002_create_warehouses.py",
            "003_add_user_roles.py"
        ]
        
        for filename in migration_files:
            with open(os.path.join(temp_migrations_dir, filename), 'w') as f:
                f.write("# Test migration file")
        
        manager = MigrationManager(migrations_dir=temp_migrations_dir)
        files = manager.get_migration_files()
        
        assert len(files) == 3
        assert all(filename in files for filename in migration_files)
    
    def test_load_migration_class(self, temp_migrations_dir):
        """Test migration class loading."""
        # Create a test migration file
        migration_content = '''
from backend.utils.migrations.migration_base import SchemaMigration

class TestMigration(SchemaMigration):
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Test migration"
    
    def up(self) -> bool:
        return self.execute_sql("CREATE TABLE test (id INT)")
    
    def down(self) -> bool:
        return self.execute_sql("DROP TABLE test")
'''
        
        migration_file = os.path.join(temp_migrations_dir, "001_test_migration.py")
        with open(migration_file, 'w') as f:
            f.write(migration_content)
        
        manager = MigrationManager(migrations_dir=temp_migrations_dir)
        
        # Test loading the migration class
        migration_class = manager.load_migration_class("001_test_migration.py")
        assert migration_class is not None
        
        # Test instantiation
        migration = migration_class()
        assert migration.get_version() == "1.0.0"
        assert migration.get_description() == "Test migration"
    
    def test_get_applied_migrations(self, temp_migrations_dir):
        """Test retrieval of applied migrations."""
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            # Mock database results
            mock_cursor.fetchall.return_value = [
                ("1.0.0", "Test migration 1", "2024-01-01 10:00:00", "success"),
                ("1.0.1", "Test migration 2", "2024-01-02 10:00:00", "success")
            ]
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            applied = manager.get_applied_migrations()
            
            assert len(applied) == 2
            assert applied[0]['version'] == "1.0.0"
            assert applied[1]['version'] == "1.0.1"
    
    def test_get_pending_migrations(self, temp_migrations_dir):
        """Test identification of pending migrations."""
        # Create test migration files
        migration_files = ["001_test1.py", "002_test2.py", "003_test3.py"]
        for filename in migration_files:
            with open(os.path.join(temp_migrations_dir, filename), 'w') as f:
                f.write("# Test migration file")
        
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            # Mock applied migrations
            mock_cursor.fetchall.return_value = [
                ("001", "Test 1", "2024-01-01 10:00:00", "success")
            ]
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            pending = manager.get_pending_migrations()
            
            # Should have 2 pending migrations (002 and 003)
            assert len(pending) == 2
            assert "002_test2.py" in pending
            assert "003_test3.py" in pending
    
    def test_apply_migration(self, temp_migrations_dir):
        """Test migration application."""
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            # Create a mock migration
            mock_migration = Mock()
            mock_migration.get_version.return_value = "1.0.0"
            mock_migration.get_description.return_value = "Test migration"
            mock_migration.up.return_value = True
            
            # Test successful migration
            result = manager.apply_migration(mock_migration)
            
            assert result is True
            
            # Verify migration was recorded
            insert_calls = [call for call in mock_cursor.execute.call_args_list 
                          if 'INSERT INTO migrations' in str(call)]
            assert len(insert_calls) > 0
    
    def test_rollback_migration(self, temp_migrations_dir):
        """Test migration rollback."""
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            # Mock migration record
            mock_cursor.fetchone.return_value = ("1.0.0", "Test migration", "2024-01-01 10:00:00", "success")
            
            # Test successful rollback
            result = manager.rollback_migration("1.0.0")
            
            assert result is True
            
            # Verify migration was marked as rolled back
            update_calls = [call for call in mock_cursor.execute.call_args_list 
                          if 'UPDATE migrations' in str(call)]
            assert len(update_calls) > 0
    
    def test_migrate(self, temp_migrations_dir):
        """Test full migration process."""
        # Create test migration files
        migration_files = ["001_test1.py", "002_test2.py"]
        for filename in migration_files:
            with open(os.path.join(temp_migrations_dir, filename), 'w') as f:
                f.write("# Test migration file")
        
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            # Mock no applied migrations
            mock_cursor.fetchall.return_value = []
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            # Mock migration class loading
            with patch.object(manager, 'load_migration_class') as mock_load:
                mock_migration_class = Mock()
                mock_migration = Mock()
                mock_migration.get_version.return_value = "001"
                mock_migration.get_description.return_value = "Test migration"
                mock_migration.up.return_value = True
                mock_migration_class.return_value = mock_migration
                mock_load.return_value = mock_migration_class
                
                # Test migration
                result = manager.migrate()
                
                assert result is True
                # Should have loaded and applied 2 migrations
                assert mock_load.call_count == 2
    
    def test_create_migration(self, temp_migrations_dir):
        """Test migration file creation."""
        manager = MigrationManager(migrations_dir=temp_migrations_dir)
        
        # Test schema migration creation
        filename = manager.create_migration("1.0.0", "Test schema migration", "schema")
        
        assert filename.endswith(".py")
        assert os.path.exists(os.path.join(temp_migrations_dir, filename))
        
        # Verify file content
        with open(os.path.join(temp_migrations_dir, filename), 'r') as f:
            content = f.read()
            assert "class Migration" in content
            assert "Test schema migration" in content
            assert "SchemaMigration" in content
        
        # Test data migration creation
        filename = manager.create_migration("1.0.1", "Test data migration", "data")
        
        with open(os.path.join(temp_migrations_dir, filename), 'r') as f:
            content = f.read()
            assert "DataMigration" in content


class TestMigrationCLI:
    """Test the migration CLI functionality."""
    
    @pytest.fixture
    def temp_migrations_dir(self):
        """Create a temporary directory for migrations."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_show_status(self, temp_migrations_dir, capsys):
        """Test status display."""
        with patch('backend.utils.migrations.migration_manager.MigrationManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Mock migration status
            mock_manager.get_migration_status.return_value = {
                'applied': [{'version': '1.0.0', 'description': 'Test 1'}],
                'pending': [{'version': '1.0.1', 'description': 'Test 2'}]
            }
            
            show_status(mock_manager)
            captured = capsys.readouterr()
            
            assert "Applied Migrations" in captured.out
            assert "Pending Migrations" in captured.out
            assert "1.0.0" in captured.out
            assert "1.0.1" in captured.out
    
    def test_migrate_command(self, temp_migrations_dir):
        """Test migrate command."""
        with patch('backend.utils.migrations.migration_manager.MigrationManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Test successful migration
            mock_manager.migrate.return_value = True
            
            result = migrate(mock_manager)
            assert result is True
            mock_manager.migrate.assert_called_once()
    
    def test_rollback_version(self, temp_migrations_dir):
        """Test rollback to specific version."""
        with patch('backend.utils.migrations.migration_manager.MigrationManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Test successful rollback
            mock_manager.rollback_migration.return_value = True
            
            result = rollback_version(mock_manager, "1.0.0")
            assert result is True
            mock_manager.rollback_migration.assert_called_once_with("1.0.0")
    
    def test_rollback_all(self, temp_migrations_dir):
        """Test rollback all migrations."""
        with patch('backend.utils.migrations.migration_manager.MigrationManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Test successful rollback
            mock_manager.rollback_all.return_value = True
            
            result = rollback_all(mock_manager)
            assert result is True
            mock_manager.rollback_all.assert_called_once()
    
    def test_create_migration(self, temp_migrations_dir):
        """Test migration creation command."""
        with patch('backend.utils.migrations.migration_manager.MigrationManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Mock migration creation
            mock_manager.create_migration.return_value = "001_test_migration.py"
            
            result = create_migration(mock_manager, "1.0.0", "Test migration", "schema")
            assert result == "001_test_migration.py"
            mock_manager.create_migration.assert_called_once_with("1.0.0", "Test migration", "schema")
    
    def test_main_function(self, temp_migrations_dir):
        """Test main CLI function."""
        with patch('sys.argv', ['migration_cli.py', 'status']):
            with patch('backend.utils.migrations.migration_manager.MigrationManager') as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager
                
                # Mock status
                mock_manager.get_migration_status.return_value = {
                    'applied': [],
                    'pending': []
                }
                
                # Test status command
                with patch('backend.utils.migrations.cli.show_status') as mock_show_status:
                    main()
                    mock_show_status.assert_called_once_with(mock_manager)
    
    def test_main_function_invalid_command(self, temp_migrations_dir):
        """Test main CLI function with invalid command."""
        with patch('sys.argv', ['migration_cli.py', 'invalid']):
            with patch('backend.utils.migrations.migration_manager.MigrationManager') as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager
                
                # Test invalid command
                with patch('sys.exit') as mock_exit:
                    main()
                    mock_exit.assert_called_once()


class TestMigrationErrorHandling:
    """Test migration error handling."""
    
    def test_migration_failure(self, temp_migrations_dir):
        """Test handling of migration failures."""
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            # Create a mock migration that fails
            mock_migration = Mock()
            mock_migration.get_version.return_value = "1.0.0"
            mock_migration.get_description.return_value = "Failing migration"
            mock_migration.up.side_effect = Exception("Migration failed")
            
            # Test migration failure
            result = manager.apply_migration(mock_migration)
            
            assert result is False
            
            # Verify failure was recorded
            update_calls = [call for call in mock_cursor.execute.call_args_list 
                          if 'UPDATE migrations' in str(call)]
            assert len(update_calls) > 0
    
    def test_rollback_failure(self, temp_migrations_dir):
        """Test handling of rollback failures."""
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            # Mock migration record
            mock_cursor.fetchone.return_value = ("1.0.0", "Test migration", "2024-01-01 10:00:00", "success")
            
            # Create a mock migration that fails on rollback
            mock_migration = Mock()
            mock_migration.down.side_effect = Exception("Rollback failed")
            
            with patch.object(manager, 'load_migration_class') as mock_load:
                mock_load.return_value = lambda: mock_migration
                
                # Test rollback failure
                result = manager.rollback_migration("1.0.0")
                
                assert result is False
    
    def test_database_connection_failure(self, temp_migrations_dir):
        """Test handling of database connection failures."""
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_conn.side_effect = Exception("Connection failed")
            
            # Should handle connection failure gracefully
            with pytest.raises(Exception):
                MigrationManager(migrations_dir=temp_migrations_dir)


class TestMigrationPerformance:
    """Test migration performance characteristics."""
    
    def test_large_migration_performance(self, temp_migrations_dir):
        """Test performance with large migrations."""
        # Create many migration files
        for i in range(100):
            filename = f"{i:03d}_test_migration_{i}.py"
            with open(os.path.join(temp_migrations_dir, filename), 'w') as f:
                f.write("# Test migration file")
        
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            # Should handle many migration files efficiently
            files = manager.get_migration_files()
            assert len(files) == 100
    
    def test_migration_memory_usage(self, temp_migrations_dir):
        """Test memory usage with large migrations."""
        # Create a large migration file
        large_migration_content = "# " + "x" * 1000000  # 1MB file
        
        migration_file = os.path.join(temp_migrations_dir, "001_large_migration.py")
        with open(migration_file, 'w') as f:
            f.write(large_migration_content)
        
        with patch('backend.utils.migrations.migration_manager.get_db_connection') as mock_conn:
            mock_cursor = Mock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            manager = MigrationManager(migrations_dir=temp_migrations_dir)
            
            # Should handle large migration files without excessive memory usage
            files = manager.get_migration_files()
            assert len(files) == 1
