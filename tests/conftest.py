import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app import create_app
from backend.config import config
from backend.utils.database import get_db_connection


@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for each test session."""
    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set test environment variables
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['FLASK_DEBUG'] = 'False'
        os.environ['DB_NAME'] = 'test_inventory_db'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        
        app = create_app()
        
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        yield app


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create a test runner for the Flask app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture(scope="function")
def mock_db_connection():
    """Mock database connection for unit tests."""
    with patch('backend.utils.database.get_db_connection') as mock:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock, mock_conn, mock_cursor


@pytest.fixture(scope="function")
def mock_execute_query():
    """Mock execute_query function for unit tests."""
    with patch('backend.utils.database.execute_query') as mock:
        yield mock


@pytest.fixture(scope="function")
def sample_user_data():
    """Sample user data for testing."""
    return {
        'id': 'user-001',
        'username': 'testuser',
        'role': 'user'
    }


@pytest.fixture(scope="function")
def sample_product_data():
    """Sample product data for testing."""
    return {
        'id': 'prod-001',
        'name': 'Test Product',
        'sku': 'TEST-001',
        'description': 'A test product for testing',
        'barcode': '1234567890123',
        'dimensions': '10x5x2 cm',
        'weight': 0.5,
        'picture_url': 'https://example.com/image.jpg',
        'batch_tracked': True
    }


@pytest.fixture(scope="function")
def sample_stock_data():
    """Sample stock item data for testing."""
    return {
        'id': 'stock-001',
        'product_id': 'prod-001',
        'bin_id': 'bin-001',
        'on_hand': 100,
        'qty_reserved': 10,
        'batch_id': 'BATCH-001',
        'expiry_date': '2024-12-31'
    }


@pytest.fixture(scope="function")
def sample_warehouse_data():
    """Sample warehouse data for testing."""
    return {
        'id': 'wh-001',
        'name': 'Test Warehouse',
        'address': '123 Test Street',
        'code': 'WH-TEST'
    }

