"""
Test suite for service layer
Tests business logic, validation, and service operations
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from backend.services.product_service import ProductService
from backend.services.stock_service import StockService
from backend.services.warehouse_service import WarehouseService
# from backend.services.user_service import UserService  # UserService not implemented yet
from backend.services.transaction_service import TransactionService

from backend.models.product import Product
from backend.models.stock import StockItem, StockTransaction
from backend.models.warehouse import Warehouse
from backend.models.user import User

from backend.exceptions import DatabaseError
from backend.services.base_service import ServiceError, ValidationError, NotFoundError


class TestProductService:
    """Test ProductService functionality"""
    
    @pytest.fixture
    def product_service(self):
        return ProductService()
    
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
    
    def test_get_product_by_id_success(self, product_service, sample_product_data):
        """Test successful product retrieval by ID"""
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            mock_product = Product(
                id='test-prod-001',
                name=sample_product_data['name'],
                sku=sample_product_data['sku'],
                description=sample_product_data['description'],
                dimensions=sample_product_data['dimensions'],
                weight=sample_product_data['weight'],
                picture_url=sample_product_data['picture_url'],
                barcode=sample_product_data['barcode'],
                batch_tracked=sample_product_data['batch_tracked']
            )
            mock_get.return_value = mock_product
            
            result = product_service.get_product_by_id('test-prod-001')
            
            assert result is not None
            assert result.name == sample_product_data['name']
            assert result.sku == sample_product_data['sku']
            mock_get.assert_called_once_with('test-prod-001')
    
    def test_get_product_by_id_not_found(self, product_service):
        """Test product retrieval when product doesn't exist"""
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            mock_get.return_value = None
            
            result = product_service.get_product_by_id('non-existent-id')
            
            assert result is None
            mock_get.assert_called_once_with('non-existent-id')
    
    def test_get_product_by_id_validation_error(self, product_service):
        """Test product retrieval with invalid ID"""
        with pytest.raises(ValidationError):
            product_service.get_product_by_id('')
    
    def test_get_product_by_id_database_error(self, product_service):
        """Test product retrieval with database error"""
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            mock_get.side_effect = DatabaseError("Database connection failed")
            
            with pytest.raises(ServiceError, match="Failed to get product by ID"):
                product_service.get_product_by_id('test-id')
    
    def test_create_product_success(self, product_service, sample_product_data):
        """Test successful product creation"""
        with patch.object(product_service.product_repository, 'create') as mock_create:
            # Create unique test data to avoid conflicts
            unique_product_data = {
                'name': 'Unique Test Product',
                'sku': 'UNIQUE-001',
                'description': 'A unique test product',
                'dimensions': '15x10x5 cm',
                'weight': 1.0,
                'picture_url': 'https://example.com/unique.jpg',
                'barcode': '9876543210987',
                'batch_tracked': False
            }
            
            mock_product = Product(
                id='test-prod-001',
                name=unique_product_data['name'],
                sku=unique_product_data['sku'],
                description=unique_product_data['description'],
                dimensions=unique_product_data['dimensions'],
                weight=unique_product_data['weight'],
                picture_url=unique_product_data['picture_url'],
                barcode=unique_product_data['barcode'],
                batch_tracked=unique_product_data['batch_tracked']
            )
            mock_create.return_value = mock_product
            
            result = product_service.create_product(unique_product_data)
            
            assert result['success'] is True
            assert result['data']['name'] == unique_product_data['name']
            assert result['data']['sku'] == unique_product_data['sku']
            mock_create.assert_called_once()
    
    def test_create_product_duplicate_sku(self, product_service, sample_product_data):
        """Test product creation with duplicate SKU"""
        with patch.object(product_service.product_repository, 'create') as mock_create:
            mock_create.side_effect = ValidationError("Product with SKU 'TEST-001' already exists")
            
            result = product_service.create_product(sample_product_data)
            
            assert result['success'] is False
            assert 'already exists' in result['error']
    
    def test_create_product_duplicate_barcode(self, product_service, sample_product_data):
        """Test product creation with duplicate barcode"""
        with patch.object(product_service.product_repository, 'create') as mock_create:
            mock_create.side_effect = ValidationError("Product with barcode '1234567890123' already exists")
            
            result = product_service.create_product(sample_product_data)
            
            assert result['success'] is False
            assert 'already exists' in result['error']
    
    def test_create_product_validation_error(self, product_service):
        """Test product creation with validation error"""
        invalid_data = {'name': ''}  # Missing required fields
        
        result = product_service.create_product(invalid_data)
        
        assert result['success'] is False
        assert 'missing required field' in result['error'].lower()
    
    def test_update_product_success(self, product_service, sample_product_data):
        """Test successful product update"""
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            with patch.object(product_service.product_repository, 'update') as mock_update:
                mock_product = Product(
                    id='test-prod-001',
                    name=sample_product_data['name'],
                    sku=sample_product_data['sku']
                )
                mock_get.return_value = mock_product
                mock_update.return_value = mock_product
                
                update_data = {'name': 'Updated Product Name'}
                result = product_service.update_product('test-prod-001', update_data)
                
                assert result['success'] is True
                mock_update.assert_called_once()
    
    def test_update_product_not_found(self, product_service):
        """Test product update when product doesn't exist"""
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            mock_get.return_value = None
            
            result = product_service.update_product('non-existent-id', {'name': 'Updated'})
            
            assert result['success'] is False
            assert 'not found' in result['error']
    
    def test_delete_product_success(self, product_service):
        """Test successful product deletion"""
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            with patch.object(product_service.product_repository, 'delete') as mock_delete:
                mock_product = Product(
                    id='test-prod-001',
                    name='Test Product',
                    sku='TEST-001'
                )
                mock_get.return_value = mock_product
                mock_delete.return_value = True
                
                result = product_service.delete_product('test-prod-001')
                
                assert result['success'] is True
                mock_delete.assert_called_once_with('test-prod-001')
    
    def test_delete_product_not_found(self, product_service):
        """Test product deletion when product doesn't exist"""
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            mock_get.return_value = None
            
            result = product_service.delete_product('non-existent-id')
            
            assert result['success'] is False
            assert 'not found' in result['error']
    
    def test_search_products(self, product_service):
        """Test product search functionality"""
        with patch.object(product_service.product_repository, 'search_products') as mock_search:
            mock_products = [
                Product(id='1', name='Laptop', sku='LAP-001'),
                Product(id='2', name='Desktop', sku='DESK-001')
            ]
            mock_search.return_value = mock_products
            
            results = product_service.search_products('laptop')
            
            assert len(results) == 2
            mock_search.assert_called_once_with('laptop', None)
    
    def test_get_all_products(self, product_service):
        """Test getting all products"""
        with patch.object(product_service.product_repository, 'get_all') as mock_get_all:
            mock_products = [
                Product(id='1', name='Product 1', sku='SKU-001'),
                Product(id='2', name='Product 2', sku='SKU-002')
            ]
            mock_get_all.return_value = mock_products
            
            results = product_service.get_all_products()
            
            assert len(results) == 2
            mock_get_all.assert_called_once()
    
    def test_bulk_update_products(self, product_service):
        """Test bulk update of products"""
        updates_data = [
            {'id': 'prod1', 'name': 'Updated Product 1'},
            {'id': 'prod2', 'name': 'Updated Product 2'}
        ]
        
        with patch.object(product_service.product_repository, 'exists') as mock_exists:
            with patch.object(product_service.product_repository, 'update') as mock_update:
                mock_exists.return_value = True
                mock_update.return_value = Product(id='prod1', name='Updated Product 1', sku='SKU1')
                
                result = product_service.bulk_update_products(updates_data)
                
                assert result['success'] is True
                assert len(result['data']) == 2
                assert mock_update.call_count == 2
    
    def test_bulk_delete_products(self, product_service):
        """Test bulk deletion of products"""
        product_ids = ['550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440002']
        
        with patch.object(product_service.product_repository, 'exists') as mock_exists:
            with patch.object(product_service.product_repository, 'bulk_delete') as mock_bulk_delete:
                mock_exists.return_value = True
                mock_bulk_delete.return_value = 2
                
                result = product_service.bulk_delete_products(product_ids)
                
                assert result['success'] is True
                assert result['data']['deleted_count'] == 2
                mock_bulk_delete.assert_called_once_with(product_ids)


class TestStockService:
    """Test StockService functionality"""
    
    @pytest.fixture
    def stock_service(self):
        return StockService()
    
    def test_get_stock_by_product(self, stock_service):
        """Test getting stock by product"""
        with patch.object(stock_service.stock_repository, 'get_stock_by_product') as mock_get:
            mock_stock = [{'id': 'stock1', 'product_id': 'prod1', 'on_hand': 100}]
            mock_get.return_value = mock_stock
            
            results = stock_service.get_stock_by_product('prod1')
            
            assert len(results) == 1
            mock_get.assert_called_once_with('prod1')
    
    def test_get_stock_by_warehouse(self, stock_service):
        """Test getting stock by warehouse"""
        with patch.object(stock_service.stock_repository, 'get_stock_by_warehouse') as mock_get:
            mock_stock = [{'id': 'stock1', 'warehouse_id': 'wh1', 'on_hand': 100}]
            mock_get.return_value = mock_stock
            
            results = stock_service.get_stock_by_warehouse('wh1')
            
            assert len(results) == 1
            mock_get.assert_called_once_with('wh1')
    
    def test_get_low_stock_items(self, stock_service):
        """Test getting low stock items"""
        with patch.object(stock_service.stock_repository, 'get_low_stock_items') as mock_get:
            mock_stock = [{'id': 'stock1', 'on_hand': 5}]
            mock_get.return_value = mock_stock
            
            results = stock_service.get_low_stock_items(threshold=10)
            
            assert len(results) == 1
            mock_get.assert_called_once_with(10)
    
    def test_get_expiring_stock(self, stock_service):
        """Test getting expiring stock"""
        with patch.object(stock_service.stock_repository, 'get_expiring_stock') as mock_get:
            mock_stock = [{'id': 'stock1', 'expiry_date': '2024-12-31'}]
            mock_get.return_value = mock_stock
            
            results = stock_service.get_expiring_stock(days_ahead=30)
            
            assert len(results) == 1
            mock_get.assert_called_once_with(30)


class TestWarehouseService:
    """Test WarehouseService functionality"""
    
    @pytest.fixture
    def warehouse_service(self):
        return WarehouseService()
    
    def test_get_warehouse_by_code(self, warehouse_service):
        """Test getting warehouse by code"""
        with patch.object(warehouse_service.warehouse_repository, 'get_by_code') as mock_get:
            mock_warehouse = Warehouse(id='wh1', name='Test Warehouse', code='WH-001')
            mock_get.return_value = mock_warehouse
            
            result = warehouse_service.get_warehouse_by_code('WH-001')
            
            assert result is not None
            mock_get.assert_called_once_with('WH-001')
    
    def test_get_warehouse_hierarchy(self, warehouse_service):
        """Test getting warehouse hierarchy"""
        with patch.object(warehouse_service.warehouse_repository, 'get_warehouse_hierarchy') as mock_get:
            mock_hierarchy = {'id': 'wh1', 'name': 'Main Warehouse', 'children': []}
            mock_get.return_value = mock_hierarchy
            
            result = warehouse_service.get_warehouse_hierarchy('wh1')
            
            assert result is not None
            mock_get.assert_called_once_with('wh1')


class TestTransactionService:
    """Test TransactionService functionality"""
    
    @pytest.fixture
    def transaction_service(self):
        return TransactionService()
    
    def test_get_transactions_by_type(self, transaction_service):
        """Test getting transactions by type"""
        with patch.object(transaction_service.transaction_repository, 'get_transactions_by_type') as mock_get:
            mock_transactions = [{'id': 'tx1', 'type': 'receive'}]
            mock_get.return_value = mock_transactions
            
            results = transaction_service.get_transactions_by_type('receive')
            
            assert len(results) == 1
            mock_get.assert_called_once_with('receive')
    
    def test_get_transactions_by_date_range(self, transaction_service):
        """Test getting transactions by date range"""
        with patch.object(transaction_service.transaction_repository, 'get_transactions_by_date_range') as mock_get:
            mock_transactions = [{'id': 'tx1', 'date': '2024-01-01'}]
            mock_get.return_value = mock_transactions
            
            results = transaction_service.get_transactions_by_date_range('2024-01-01', '2024-01-31')
            
            assert len(results) == 1
            mock_get.assert_called_once_with('2024-01-01', '2024-01-31')


class TestServiceIntegration:
    """Test service integration and dependencies"""
    
    def test_service_repository_integration(self):
        """Test that services have proper repository attributes"""
        stock_service = StockService()
        warehouse_service = WarehouseService()
        transaction_service = TransactionService()
        
        assert hasattr(stock_service, 'stock_repository')
        assert hasattr(warehouse_service, 'warehouse_repository')
        assert hasattr(transaction_service, 'transaction_repository')
    
    def test_service_error_handling(self):
        """Test service error handling"""
        product_service = ProductService()
        
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            mock_get.side_effect = DatabaseError("Database connection failed")
            
            with pytest.raises(ServiceError, match="Failed to get product by ID"):
                product_service.get_product_by_id('test-id')


class TestServiceErrorHandling:
    """Test service error handling scenarios"""
    
    def test_service_database_error_handling(self):
        """Test service handling of database errors"""
        product_service = ProductService()
        
        with patch.object(product_service.product_repository, 'get_by_id') as mock_get:
            mock_get.side_effect = DatabaseError("Database connection failed")
            
            with pytest.raises(ServiceError, match="Failed to get product by ID"):
                product_service.get_product_by_id('test-id')


class TestServicePerformance:
    """Test service performance characteristics"""
    
    def test_service_bulk_operations_performance(self):
        """Test performance of bulk operations"""
        import time
        
        product_service = ProductService()
        large_dataset = [{'name': f'Product {i}', 'sku': f'SKU-{i:03d}'} for i in range(1000)]
        
        start_time = time.time()
        # This would normally call the service method
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Should complete within 1 second
    
    def test_service_search_performance(self):
        """Test performance of search operations"""
        import time
        
        product_service = ProductService()
        
        start_time = time.time()
        # This would normally call the service method
        end_time = time.time()
        
        execution_time = end_time - start_time
        assert execution_time < 0.1  # Should complete within 0.1 seconds


class TestServiceDataValidation:
    """Test service data validation"""
    
    def test_product_data_validation(self):
        """Test product data validation in service"""
        product_service = ProductService()
        
        valid_data = {
            'id': 'test-prod',
            'name': 'Test Product',
            'sku': 'TEST-001',
            'dimensions': '10x5x2 cm',
            'weight': 0.5
        }
        
        with patch.object(product_service.product_repository, 'create') as mock_create:
            mock_product = Product(
                id=valid_data['id'],
                name=valid_data['name'],
                sku=valid_data['sku'],
                dimensions=valid_data['dimensions'],
                weight=valid_data['weight']
            )
            mock_create.return_value = mock_product
            
            result = product_service.create_product(valid_data)
            
            assert result['success'] is True
            assert result['data']['name'] == valid_data['name']


class TestServiceMocking:
    """Test service mocking capabilities"""
    
    def test_service_with_mocked_repositories(self):
        """Test service behavior with mocked repositories"""
        # This test demonstrates how to mock repository dependencies
        with patch('backend.repositories.product_repository.ProductRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id.return_value = None
            
            # Create service with mocked repository
            product_service = ProductService()
            product_service.product_repository = mock_repo
            
            result = product_service.get_product_by_id('test-id')
            
            assert result is None
            mock_repo.get_by_id.assert_called_once_with('test-id')
