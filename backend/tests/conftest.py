import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from typing import Generator, Dict, Any

# Import the models and repositories
from backend.models.product import Product
from backend.models.stock import StockItem
from backend.models.warehouse import Warehouse
from backend.models.user import User
from backend.models.stock import StockTransaction

from backend.repositories.product_repository import ProductRepository
from backend.repositories.stock_repository import StockRepository
from backend.repositories.warehouse_repository import WarehouseRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.transaction_repository import TransactionRepository

from backend.utils.database import get_db_connection, execute_query
from backend.utils.migrations.migration_manager import MigrationManager

# Import test configuration
from backend.tests.test_config import (
    TEST_DB_CONFIG, CREATE_TEST_TABLES_SQL, INSERT_TEST_DATA_SQL, CLEANUP_TEST_TABLES_SQL,
    SAMPLE_PRODUCT_DATA, SAMPLE_WAREHOUSE_DATA, SAMPLE_LOCATION_DATA, SAMPLE_BIN_DATA,
    SAMPLE_STOCK_DATA, SAMPLE_USER_DATA, SAMPLE_TRANSACTION_DATA, generate_uuid
)

@pytest.fixture(scope="session")
def test_database():
    """Create a test database and clean it up after all tests."""
    # Create test database
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        cursor.execute("CREATE DATABASE inventory_test")
    except Exception:
        pass  # Database might already exist
    
    cursor.close()
    conn.close()
    
    yield TEST_DB_CONFIG
    
    # Cleanup test database
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        cursor.execute("DROP DATABASE inventory_test")
    except Exception:
        pass
    
    cursor.close()
    conn.close()

@pytest.fixture
def db_connection(test_database):
    """Provide a database connection for tests."""
    conn = get_db_connection()
    yield conn
    conn.rollback()
    conn.close()

@pytest.fixture
def db_cursor(db_connection):
    """Provide a database cursor for tests."""
    cursor = db_connection.cursor()
    yield cursor
    cursor.close()

@pytest.fixture
def migration_manager():
    """Provide a migration manager for testing migrations."""
    temp_dir = tempfile.mkdtemp()
    manager = MigrationManager(migrations_dir=temp_dir)
    
    yield manager
    
    # Cleanup
    shutil.rmtree(temp_dir)

# Repository fixtures
@pytest.fixture
def product_repository():
    """Provide a product repository for testing."""
    return ProductRepository()

@pytest.fixture
def stock_repository():
    """Provide a stock repository for testing."""
    return StockRepository()

@pytest.fixture
def warehouse_repository():
    """Provide a warehouse repository for testing."""
    return WarehouseRepository()

@pytest.fixture
def user_repository():
    """Provide a user repository for testing."""
    return UserRepository()

@pytest.fixture
def transaction_repository():
    """Provide a transaction repository for testing."""
    return TransactionRepository()

# Sample data fixtures
@pytest.fixture
def sample_product_data() -> Dict[str, Any]:
    """Provide sample product data for testing."""
    data = SAMPLE_PRODUCT_DATA.copy()
    data['id'] = generate_uuid()
    return data

@pytest.fixture
def sample_stock_data() -> Dict[str, Any]:
    """Provide sample stock data for testing."""
    return {
        'id': 'test-stock-001',
        'product_id': 'test-prod-001',
        'warehouse_id': 'test-warehouse-001',
        'location_id': 'test-location-001',
        'bin_id': 'test-bin-001',
        'quantity': 50,
        'batch_number': 'BATCH-001',
        'expiry_date': '2025-12-31',
        'status': 'available',
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z'
    }

@pytest.fixture
def sample_warehouse_data() -> Dict[str, Any]:
    """Provide sample warehouse data for testing."""
    return {
        'id': 'test-warehouse-001',
        'name': 'Test Warehouse',
        'code': 'TEST-WH',
        'address': '123 Test Street',
        'city': 'Test City',
        'state': 'Test State',
        'country': 'Test Country',
        'postal_code': '12345',
        'contact_person': 'Test Contact',
        'contact_email': 'test@example.com',
        'contact_phone': '+1-555-0123',
        'capacity': 1000,
        'parent_warehouse_id': None,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z'
    }

@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Provide sample user data for testing."""
    return {
        'id': 'test-user-001',
        'username': 'testuser',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'role': 'user',
        'warehouse_id': 'test-warehouse-001',
        'is_active': True,
        'last_login': '2024-01-01T00:00:00Z',
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z'
    }

@pytest.fixture
def sample_transaction_data() -> Dict[str, Any]:
    """Provide sample transaction data for testing."""
    return {
        'id': 'test-trans-001',
        'transaction_type': 'in',
        'stock_item_id': 'test-stock-001',
        'quantity': 25,
        'user_id': 'test-user-001',
        'warehouse_id': 'test-warehouse-001',
        'reference_number': 'REF-001',
        'notes': 'Test transaction',
        'transaction_date': '2024-01-01T00:00:00Z',
        'created_at': '2024-01-01T00:00:00Z'
    }

# Mock fixtures for external dependencies
@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing without real database."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.rollback.return_value = None
    mock_conn.close.return_value = None
    return mock_conn, mock_cursor

@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock()

# Test utilities
@pytest.fixture
def create_test_tables(db_connection):
    """Create test tables for testing."""
    cursor = db_connection.cursor()
    
    # Create test tables using the actual schema
    for sql in CREATE_TEST_TABLES_SQL:
        cursor.execute(sql)
    
    db_connection.commit()
    cursor.close()
    
    yield
    
    # Cleanup test tables
    cursor = db_connection.cursor()
    for sql in CLEANUP_TEST_TABLES_SQL:
        cursor.execute(sql)
    
    db_connection.commit()
    cursor.close()

@pytest.fixture
def populate_test_data(db_connection, sample_product_data, sample_warehouse_data, 
                      sample_user_data, sample_stock_data, sample_transaction_data):
    """Populate test tables with sample data."""
    cursor = db_connection.cursor()
    
    # Insert test data in proper order (respecting foreign key constraints)
    cursor.execute(INSERT_TEST_DATA_SQL[0], sample_product_data)
    cursor.execute(INSERT_TEST_DATA_SQL[1], sample_warehouse_data)
    
    # Create location and bin data
    location_data = SAMPLE_LOCATION_DATA.copy()
    location_data['id'] = generate_uuid()
    location_data['warehouse_id'] = sample_warehouse_data['id']
    
    bin_data = SAMPLE_BIN_DATA.copy()
    bin_data['id'] = generate_uuid()
    bin_data['location_id'] = location_data['id']
    
    cursor.execute(INSERT_TEST_DATA_SQL[2], location_data)
    cursor.execute(INSERT_TEST_DATA_SQL[3], bin_data)
    
    # Update stock data with proper foreign keys
    stock_data = sample_stock_data.copy()
    stock_data['product_id'] = sample_product_data['id']
    stock_data['bin_id'] = bin_data['id']
    
    # Update user data with proper foreign keys
    user_data = sample_user_data.copy()
    user_data['warehouse_id'] = sample_warehouse_data['id']
    
    cursor.execute(INSERT_TEST_DATA_SQL[4], stock_data)
    cursor.execute(INSERT_TEST_DATA_SQL[5], user_data)
    
    # Update transaction data with proper foreign keys
    transaction_data = sample_transaction_data.copy()
    transaction_data['stock_item_id'] = stock_data['id']
    transaction_data['user_id'] = user_data['id']
    transaction_data['warehouse_id'] = sample_warehouse_data['id']
    
    cursor.execute(INSERT_TEST_DATA_SQL[6], transaction_data)
    
    db_connection.commit()
    cursor.close()

# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (deselect with '-m \"not unit\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their names."""
    for item in items:
        if "test_repository_" in item.name:
            item.add_marker(pytest.mark.integration)
        elif "test_migration_" in item.name:
            item.add_marker(pytest.mark.integration)
        elif "test_database_" in item.name:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
