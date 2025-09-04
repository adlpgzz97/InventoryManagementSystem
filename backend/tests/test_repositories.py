"""
Test suite for repository layer
Tests data access, CRUD operations, and database interactions
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from backend.repositories.product_repository import ProductRepository
from backend.repositories.stock_repository import StockRepository
from backend.repositories.warehouse_repository import WarehouseRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.transaction_repository import TransactionRepository

from backend.models.product import Product
from backend.models.stock import StockItem, StockTransaction
from backend.models.warehouse import Warehouse
from backend.models.user import User

from backend.exceptions import DatabaseError, ConnectionError


class TestBaseRepository:
    """Test BaseRepository functionality"""
    
    @pytest.fixture
    def base_repository(self):
        return ProductRepository()
    
    def test_get_cursor_success(self, base_repository):
        """Test successful cursor acquisition"""
        with patch('backend.repositories.base_repository.get_db_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            with base_repository.get_cursor() as cursor:
                assert cursor == mock_cursor
    
    def test_get_cursor_rollback_on_error(self, base_repository):
        """Test cursor rollback on error"""
        with patch('backend.repositories.base_repository.get_db_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            # Simulate an error during cursor usage
            with pytest.raises(Exception):
                with base_repository.get_cursor() as cursor:
                    raise Exception("Test error")
            
            # Verify cursor was closed
            mock_cursor.close.assert_called_once()


class TestProductRepository:
    """Test ProductRepository functionality"""
    
    @pytest.fixture
    def product_repository(self):
        return ProductRepository()
    
    @pytest.fixture
    def sample_product_data(self):
        return {
            'name': 'Test Product',
            'sku': 'TEST-001',
            'description': 'A test product for testing',
            'dimensions': '10x5x2 cm',
            'weight': 0.5,
            'picture_url': 'https://example.com/test.jpg',
            'barcode': '1234567890123',
            'batch_tracked': True
        }
    
    def test_create_product(self, product_repository, sample_product_data):
        """Test product creation"""
        with patch.object(product_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.description = [
                ('id',), ('name',), ('sku',), ('description',), ('dimensions',), 
                ('weight',), ('picture_url',), ('barcode',), ('batch_tracked',), ('created_at',)
            ]
            mock_cursor.fetchone.return_value = (
                'test-uuid-123', sample_product_data['name'], sample_product_data['sku'],
                sample_product_data['description'], sample_product_data['dimensions'],
                sample_product_data['weight'], sample_product_data['picture_url'],
                sample_product_data['barcode'], sample_product_data['batch_tracked'], datetime.now()
            )
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = product_repository.create(sample_product_data)
            
            assert result is not None
            assert result.name == sample_product_data['name']
            assert result.sku == sample_product_data['sku']
    
    def test_get_product_by_id(self, product_repository):
        """Test product retrieval by ID"""
        with patch.object(product_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-uuid-123',
                'name': 'Test Product',
                'sku': 'TEST-001',
                'description': 'A test product',
                'dimensions': '10x5x2 cm',
                'weight': 0.5,
                'picture_url': 'https://example.com/test.jpg',
                'barcode': '1234567890123',
                'batch_tracked': True,
                'created_at': datetime.now()
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = product_repository.get_by_id('test-uuid-123')
            
            assert result is not None
            assert result.name == 'Test Product'
            assert result.sku == 'TEST-001'
    
    def test_get_product_by_sku(self, product_repository):
        """Test product retrieval by SKU"""
        with patch.object(product_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-uuid-123',
                'name': 'Test Product',
                'sku': 'TEST-001',
                'description': 'A test product',
                'dimensions': '10x5x2 cm',
                'weight': 0.5,
                'picture_url': 'https://example.com/test.jpg',
                'barcode': '1234567890123',
                'batch_tracked': True,
                'created_at': datetime.now()
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = product_repository.get_by_sku('TEST-001')
            
            assert result is not None
            assert result.sku == 'TEST-001'
    
    def test_get_product_by_barcode(self, product_repository):
        """Test product retrieval by barcode"""
        with patch.object(product_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-uuid-123',
                'name': 'Test Product',
                'sku': 'TEST-001',
                'description': 'A test product',
                'dimensions': '10x5x2 cm',
                'weight': 0.5,
                'picture_url': 'https://example.com/test.jpg',
                'barcode': '1234567890123',
                'batch_tracked': True,
                'created_at': datetime.now()
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = product_repository.get_by_barcode('1234567890123')
            
            assert result is not None
            assert result.barcode == '1234567890123'
    
    def test_get_products_by_category(self, product_repository):
        """Test product retrieval by category - note: category column doesn't exist in schema"""
        # This test should be skipped or modified since category column doesn't exist
        pytest.skip("Category column not present in current schema")
    
    def test_get_low_stock_products(self, product_repository):
        """Test low stock products retrieval"""
        with patch.object(product_repository, 'execute_custom_query') as mock_execute:
            mock_execute.return_value = [
                {'product_id': 'prod1', 'current_stock': 5},
                {'product_id': 'prod2', 'current_stock': 3}
            ]
            
            results = product_repository.get_low_stock_products(threshold=10)
            
            assert len(results) == 2
            mock_execute.assert_called_once()
    
    def test_update_product(self, product_repository):
        """Test product update"""
        with patch.object(product_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-uuid-123',
                'name': 'Updated Product',
                'sku': 'TEST-001',
                'description': 'Updated description',
                'dimensions': '15x10x5 cm',
                'weight': 1.0,
                'picture_url': 'https://example.com/updated.jpg',
                'barcode': '1234567890123',
                'batch_tracked': True,
                'created_at': datetime.now()
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            update_data = {'name': 'Updated Product', 'description': 'Updated description'}
            result = product_repository.update('test-uuid-123', update_data)
            
            assert result is not None
            assert result.name == 'Updated Product'
    
    def test_bulk_create_products(self, product_repository, sample_product_data):
        """Test bulk product creation"""
        products_data = [sample_product_data, sample_product_data]
        
        with patch.object(product_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-uuid-123',
                'name': sample_product_data['name'],
                'sku': sample_product_data['sku']
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            results = product_repository.bulk_create(products_data)
            
            assert len(results) == 2
            assert all(isinstance(result, Product) for result in results)


class TestStockRepository:
    """Test StockRepository functionality"""
    
    @pytest.fixture
    def stock_repository(self):
        return StockRepository()
    
    @pytest.fixture
    def sample_stock_data(self):
        return {
            'product_id': 'test-prod-uuid',
            'bin_id': 'test-bin-uuid',
            'on_hand': 100,
            'qty_reserved': 0,
            'batch_id': 'BATCH-001',
            'expiry_date': (datetime.now() + timedelta(days=30)).date(),
            'received_date': datetime.now()
        }
    
    def test_create_stock_item(self, stock_repository, sample_stock_data):
        """Test stock item creation"""
        with patch.object(stock_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-stock-uuid',
                'product_id': sample_stock_data['product_id'],
                'bin_id': sample_stock_data['bin_id'],
                'on_hand': sample_stock_data['on_hand'],
                'qty_reserved': sample_stock_data['qty_reserved'],
                'batch_id': sample_stock_data['batch_id'],
                'expiry_date': sample_stock_data['expiry_date'],
                'received_date': sample_stock_data['received_date'],
                'created_at': datetime.now()
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = stock_repository.create(sample_stock_data)
            
            assert result is not None
            assert result.product_id == sample_stock_data['product_id']
            assert result.bin_id == sample_stock_data['bin_id']
    
    def test_get_stock_by_product(self, stock_repository):
        """Test stock retrieval by product"""
        with patch.object(stock_repository, 'find_by') as mock_find_by:
            mock_stock_items = [
                StockItem(id='stock1', product_id='prod1', bin_id='bin1', on_hand=100, qty_reserved=0),
                StockItem(id='stock2', product_id='prod1', bin_id='bin2', on_hand=50, qty_reserved=10)
            ]
            mock_find_by.return_value = mock_stock_items
            
            results = stock_repository.get_stock_by_product('prod1')
            
            assert len(results) == 2
            assert all(item.product_id == 'prod1' for item in results)
    
    def test_get_stock_by_warehouse(self, stock_repository):
        """Test stock retrieval by warehouse"""
        with patch.object(stock_repository, 'execute_custom_query') as mock_execute:
            mock_execute.return_value = [
                {'id': 'stock1', 'warehouse_id': 'wh1', 'on_hand': 100},
                {'id': 'stock2', 'warehouse_id': 'wh1', 'on_hand': 50}
            ]
            
            results = stock_repository.get_stock_by_warehouse('wh1')
            
            assert len(results) == 2
            assert all(item['warehouse_id'] == 'wh1' for item in results)
    
    def test_get_low_stock_items(self, stock_repository):
        """Test low stock items retrieval"""
        with patch.object(stock_repository, 'execute_custom_query') as mock_execute:
            mock_execute.return_value = [
                {'id': 'stock1', 'on_hand': 5, 'qty_reserved': 0},
                {'id': 'stock2', 'on_hand': 3, 'qty_reserved': 1}
            ]
            
            results = stock_repository.get_low_stock_items(threshold=10)
            
            assert len(results) == 2
            assert all(item['on_hand'] < 10 for item in results)
    
    def test_get_expiring_stock(self, stock_repository):
        """Test expiring stock retrieval"""
        with patch.object(stock_repository, 'execute_custom_query') as mock_execute:
            mock_execute.return_value = [
                {'id': 'stock1', 'expiry_date': '2024-12-31'},
                {'id': 'stock2', 'expiry_date': '2024-12-30'}
            ]
            
            results = stock_repository.get_expiring_stock(days_ahead=30)
            
            assert len(results) == 2
            mock_execute.assert_called_once_with(mock_execute.return_value, (30,))
    
    def test_reserve_stock(self, stock_repository):
        """Test stock reservation"""
        with patch.object(stock_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (100, 0)  # on_hand, qty_reserved
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = stock_repository.reserve_stock('stock1', 10, 'user1')
            
            assert result is True
            mock_cursor.execute.assert_called()
    
    def test_release_stock(self, stock_repository):
        """Test stock reservation release"""
        with patch.object(stock_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = stock_repository.release_stock('stock1', 10, 'user1')
            
            assert result is True
            mock_cursor.execute.assert_called()


class TestWarehouseRepository:
    """Test WarehouseRepository functionality"""
    
    @pytest.fixture
    def warehouse_repository(self):
        return WarehouseRepository()
    
    @pytest.fixture
    def sample_warehouse_data(self):
        return {
            'name': 'Test Warehouse',
            'address': '123 Test Street, Test City, TC 12345',
            'code': 'WH-001'
        }
    
    def test_create_warehouse(self, warehouse_repository, sample_warehouse_data):
        """Test warehouse creation"""
        with patch.object(warehouse_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-warehouse-uuid',
                'name': sample_warehouse_data['name'],
                'address': sample_warehouse_data['address'],
                'code': sample_warehouse_data['code']
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = warehouse_repository.create(sample_warehouse_data)
            
            assert result is not None
            assert result.name == sample_warehouse_data['name']
            assert result.code == sample_warehouse_data['code']
    
    def test_get_warehouse_by_code(self, warehouse_repository):
        """Test warehouse retrieval by code"""
        with patch.object(warehouse_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-warehouse-uuid',
                'name': 'Test Warehouse',
                'address': '123 Test Street',
                'code': 'WH-001'
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = warehouse_repository.get_by_code('WH-001')
            
            assert result is not None
            assert result.code == 'WH-001'
    
    def test_get_warehouse_stock_summary(self, warehouse_repository):
        """Test warehouse stock summary retrieval"""
        with patch.object(warehouse_repository, 'execute_custom_query') as mock_execute:
            mock_execute.return_value = [
                {'product_id': 'prod1', 'total_stock': 100},
                {'product_id': 'prod2', 'total_stock': 50}
            ]
            
            results = warehouse_repository.get_warehouse_stock_summary('warehouse1')
            
            assert len(results) == 2
            mock_execute.assert_called_once()


class TestUserRepository:
    """Test UserRepository functionality"""
    
    @pytest.fixture
    def user_repository(self):
        return UserRepository()
    
    @pytest.fixture
    def sample_user_data(self):
        return {
            'username': 'testuser',
            'password_hash': 'hashed_password_123',
            'role': 'worker'
        }
    
    def test_create_user(self, user_repository, sample_user_data):
        """Test user creation"""
        with patch.object(user_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-user-uuid',
                'username': sample_user_data['username'],
                'password_hash': sample_user_data['password_hash'],
                'role': sample_user_data['role'],
                'created_at': datetime.now()
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = user_repository.create(sample_user_data)
            
            assert result is not None
            assert result.username == sample_user_data['username']
            assert result.role == sample_user_data['role']
    
    def test_get_user_by_username(self, user_repository):
        """Test user retrieval by username"""
        with patch.object(user_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-user-uuid',
                'username': 'testuser',
                'password_hash': 'hashed_password_123',
                'role': 'worker',
                'created_at': datetime.now()
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = user_repository.get_by_username('testuser')
            
            assert result is not None
            assert result.username == 'testuser'
    
    def test_get_active_users(self, user_repository):
        """Test active users retrieval"""
        with patch.object(user_repository, 'find_by') as mock_find_by:
            mock_users = [
                User(id='user1', username='user1', role='worker'),
                User(id='user2', username='user2', role='manager')
            ]
            mock_find_by.return_value = mock_users
            
            results = user_repository.get_active_users()
            
            assert len(results) == 2
            assert all(isinstance(user, User) for user in results)


class TestTransactionRepository:
    """Test TransactionRepository functionality"""
    
    @pytest.fixture
    def transaction_repository(self):
        return TransactionRepository()
    
    @pytest.fixture
    def sample_transaction_data(self):
        return {
            'stock_item_id': 'test-stock-uuid',
            'transaction_type': 'receive',
            'quantity_change': 50,
            'quantity_before': 0,
            'quantity_after': 50,
            'reference_id': None,
            'notes': 'Test transaction',
            'user_id': 'test-user-uuid'
        }
    
    def test_create_transaction(self, transaction_repository, sample_transaction_data):
        """Test transaction creation"""
        with patch.object(transaction_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-transaction-uuid',
                'stock_item_id': sample_transaction_data['stock_item_id'],
                'transaction_type': sample_transaction_data['transaction_type'],
                'quantity_change': sample_transaction_data['quantity_change'],
                'quantity_before': sample_transaction_data['quantity_before'],
                'quantity_after': sample_transaction_data['quantity_after'],
                'reference_id': sample_transaction_data['reference_id'],
                'notes': sample_transaction_data['notes'],
                'user_id': sample_transaction_data['user_id'],
                'created_at': datetime.now()
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            result = transaction_repository.create(sample_transaction_data)
            
            assert result is not None
            assert result.stock_item_id == sample_transaction_data['stock_item_id']
            assert result.transaction_type == sample_transaction_data['transaction_type']
    
    def test_get_transactions_by_type(self, transaction_repository):
        """Test transaction retrieval by type"""
        with patch.object(transaction_repository, 'find_by') as mock_find_by:
            mock_transactions = [
                StockTransaction(
                    id='tx1', stock_item_id='stock1', transaction_type='receive',
                    quantity_change=50, quantity_before=0, quantity_after=50,
                    user_id='user1'
                ),
                StockTransaction(
                    id='tx2', stock_item_id='stock2', transaction_type='receive',
                    quantity_change=30, quantity_before=0, quantity_after=30,
                    user_id='user1'
                )
            ]
            mock_find_by.return_value = mock_transactions
            
            results = transaction_repository.get_transactions_by_type('receive')
            
            assert len(results) == 2
            assert all(tx.transaction_type == 'receive' for tx in results)
    
    def test_get_transaction_statistics(self, transaction_repository):
        """Test transaction statistics retrieval"""
        with patch.object(transaction_repository, 'execute_custom_query') as mock_execute:
            mock_execute.return_value = [
                {'transaction_type': 'receive', 'count': 10},
                {'transaction_type': 'ship', 'count': 5}
            ]
            
            results = transaction_repository.get_transaction_statistics()
            
            assert len(results) == 2
            assert results[0]['transaction_type'] == 'receive'
            assert results[1]['transaction_type'] == 'ship'


class TestRepositoryErrorHandling:
    """Test repository error handling"""
    
    def test_database_connection_error(self):
        """Test handling of database connection errors"""
        with patch('backend.repositories.base_repository.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.side_effect = ConnectionError("Database connection failed")
            
            product_repository = ProductRepository()
            
            with pytest.raises(ConnectionError):
                with product_repository.get_cursor():
                    pass
    
    def test_transaction_rollback_on_error(self):
        """Test transaction rollback on error"""
        with patch('backend.repositories.base_repository.get_db_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            product_repository = ProductRepository()
            
            with pytest.raises(Exception):
                with product_repository.get_cursor() as cursor:
                    raise Exception("Test error")
            
            # Verify rollback was called
            mock_cursor.rollback.assert_called_once()


class TestRepositoryPerformance:
    """Test repository performance characteristics"""
    
    def test_bulk_operations_efficiency(self):
        """Test efficiency of bulk operations"""
        product_repository = ProductRepository()
        
        # Create many products for bulk operation
        products_data = [
            {
                'name': f'Product {i}',
                'sku': f'SKU-{i:03d}',
                'description': f'Description for product {i}',
                'dimensions': f'{i}x{i}x{i} cm',
                'weight': float(i),
                'picture_url': f'https://example.com/product{i}.jpg',
                'barcode': f'123456789012{i:01d}',
                'batch_tracked': i % 2 == 0
            }
            for i in range(100)
        ]
        
        with patch.object(product_repository, 'get_cursor') as mock_get_cursor:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {
                'id': 'test-uuid-123',
                'name': 'Test Product',
                'sku': 'TEST-001'
            }
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_cursor.return_value.__exit__.return_value = None
            
            start_time = datetime.now()
            results = product_repository.bulk_create(products_data)
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            assert execution_time < 1.0  # Should complete in under 1 second
            assert len(results) == 100
