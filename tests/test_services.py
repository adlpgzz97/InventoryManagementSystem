import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime

from backend.services.base_service import BaseService, ServiceError, ValidationError, NotFoundError
from backend.services.dashboard_service import DashboardService
from backend.services.product_service import ProductService
from backend.services.stock_service import StockService
from backend.services.warehouse_service import WarehouseService
from backend.services.transaction_service import TransactionService
from backend.services.scanner_service import ScannerService
from backend.services.simple_auth_service import SimpleAuthService
from backend.services.service_orchestrator import ServiceOrchestrator


class TestBaseService:
    """Test cases for BaseService."""
    
    def test_base_service_initialization(self):
        """Test BaseService initialization."""
        service = BaseService()
        assert service.logger is not None
    
    def test_validate_required_fields_success(self):
        """Test successful validation of required fields."""
        service = BaseService()
        data = {'name': 'Test', 'email': 'test@example.com'}
        required_fields = ['name', 'email']
        
        # Should not raise an exception
        service._validate_required_fields(data, required_fields)
    
    def test_validate_required_fields_missing(self):
        """Test validation failure when required fields are missing."""
        service = BaseService()
        data = {'name': 'Test'}
        required_fields = ['name', 'email']
        
        with pytest.raises(ValidationError, match="Missing required field: email"):
            service._validate_required_fields(data, required_fields)
    
    def test_format_response_success(self):
        """Test successful response formatting."""
        service = BaseService()
        data = {'id': 1, 'name': 'Test'}
        
        response = service._format_response(True, data=data, message="Success")
        
        assert response['success'] is True
        assert response['data'] == data
        assert response['message'] == "Success"
        assert 'timestamp' in response
    
    def test_format_response_error(self):
        """Test error response formatting."""
        service = BaseService()
        
        response = service._format_response(False, error="Test error")
        
        assert response['success'] is False
        assert response['error'] == "Test error"
        assert 'timestamp' in response


class TestDashboardService:
    """Test cases for DashboardService."""
    
    def test_dashboard_service_initialization(self):
        """Test DashboardService initialization."""
        service = DashboardService()
        assert isinstance(service, BaseService)
    
    @patch('backend.services.dashboard_service.execute_query')
    def test_get_dashboard_stats_success(self, mock_execute_query):
        """Test successful dashboard statistics retrieval."""
        mock_execute_query.side_effect = [
            [{'count': 10}],  # Total products
            [{'count': 5}],   # Total warehouses
            [{'count': 1000}], # Total stock items
            [{'count': 50}]    # Total users
        ]
        
        service = DashboardService()
        stats = service.get_dashboard_stats()
        
        assert stats['success'] is True
        assert stats['data']['total_products'] == 10
        assert stats['data']['total_warehouses'] == 5
        assert stats['data']['total_stock_items'] == 1000
        assert stats['data']['total_users'] == 50
    
    @patch('backend.services.dashboard_service.execute_query')
    def test_get_dashboard_stats_database_error(self, mock_execute_query):
        """Test dashboard statistics retrieval with database error."""
        mock_execute_query.side_effect = Exception("Database connection failed")
        
        service = DashboardService()
        stats = service.get_dashboard_stats()
        
        assert stats['success'] is False
        assert "Database connection failed" in stats['error']


class TestProductService:
    """Test cases for ProductService."""
    
    def test_product_service_initialization(self):
        """Test ProductService initialization."""
        service = ProductService()
        assert isinstance(service, BaseService)
    
    @patch('backend.services.product_service.execute_query')
    def test_get_product_by_id_success(self, mock_execute_query):
        """Test successful product retrieval by ID."""
        mock_execute_query.return_value = {
            'id': 'prod-001',
            'name': 'Test Product',
            'sku': 'TEST-001',
            'description': 'A test product',
            'barcode': '1234567890123'
        }
        
        service = ProductService()
        result = service.get_product_by_id('prod-001')
        
        assert result is not None
        assert result.id == 'prod-001'
        assert result.name == 'Test Product'
        mock_execute_query.assert_called_once()
    
    @patch('backend.services.product_service.execute_query')
    def test_get_product_by_id_not_found(self, mock_execute_query):
        """Test product retrieval when product doesn't exist."""
        mock_execute_query.return_value = None
        
        service = ProductService()
        result = service.get_product_by_id('nonexistent')
        
        assert result is None
        mock_execute_query.assert_called_once()
    
    @patch('backend.services.product_service.execute_query')
    def test_create_product_success(self, mock_execute_query):
        """Test successful product creation."""
        product_data = {
            'name': 'New Product',
            'sku': 'NEW-001',
            'description': 'A new product',
            'barcode': '1234567890123'
        }
        
        mock_execute_query.return_value = 'prod-002'
        
        service = ProductService()
        result = service.create_product(product_data)
        
        assert result['success'] is True
        assert result['data']['id'] == 'prod-002'
        assert result['message'] == "Product created successfully"
    
    def test_create_product_validation_failure(self):
        """Test product creation with validation failure."""
        product_data = {
            # Missing required fields
        }
        
        service = ProductService()
        result = service.create_product(product_data)
        
        assert result['success'] is False
        assert "Missing required field" in result['error']


class TestStockService:
    """Test cases for StockService."""
    
    def test_stock_service_initialization(self):
        """Test StockService initialization."""
        service = StockService()
        assert isinstance(service, BaseService)
    
    @patch('backend.services.stock_service.StockItem')
    def test_get_stock_levels_success(self, mock_stock_class):
        """Test successful stock levels retrieval."""
        mock_stock_items = [
            MagicMock(id='stock-001', on_hand=100, qty_reserved=10, available_stock=90),
            MagicMock(id='stock-002', on_hand=50, qty_reserved=5, available_stock=45)
        ]
        mock_stock_class.get_all.return_value = mock_stock_items
        
        service = StockService()
        result = service.get_stock_levels()
        
        assert result['success'] is True
        assert len(result['data']) == 2
        assert result['data'][0]['available_stock'] == 90
    
    @patch('backend.services.stock_service.StockItem')
    def test_reserve_stock_success(self, mock_stock_class):
        """Test successful stock reservation."""
        mock_stock_item = MagicMock()
        mock_stock_item.on_hand = 100
        mock_stock_item.qty_reserved = 10
        mock_stock_item.available_stock = 90
        
        mock_stock_class.get_by_id.return_value = mock_stock_item
        
        service = StockService()
        result = service.reserve_stock('stock-001', 20)
        
        assert result['success'] is True
        assert result['message'] == "Stock reserved successfully"
    
    def test_reserve_stock_insufficient_quantity(self):
        """Test stock reservation with insufficient quantity."""
        service = StockService()
        result = service.reserve_stock('stock-001', 200)  # More than available
        
        assert result['success'] is False
        assert "Insufficient stock" in result['error']


class TestWarehouseService:
    """Test cases for WarehouseService."""
    
    def test_warehouse_service_initialization(self):
        """Test WarehouseService initialization."""
        service = WarehouseService()
        assert isinstance(service, BaseService)
    
    @patch('backend.services.warehouse_service.Warehouse')
    def test_get_warehouse_by_id_success(self, mock_warehouse_class):
        """Test successful warehouse retrieval by ID."""
        mock_warehouse = MagicMock()
        mock_warehouse.id = 'wh-001'
        mock_warehouse.name = 'Test Warehouse'
        mock_warehouse_class.get_by_id.return_value = mock_warehouse
        
        service = WarehouseService()
        result = service.get_warehouse_by_id('wh-001')
        
        assert result['success'] is True
        assert result['data']['id'] == 'wh-001'
        assert result['data']['name'] == 'Test Warehouse'
    
    @patch('backend.services.warehouse_service.Location')
    def test_get_warehouse_locations_success(self, mock_location_class):
        """Test successful warehouse locations retrieval."""
        mock_locations = [
            MagicMock(id='loc-001', name='Aisle A1'),
            MagicMock(id='loc-002', name='Aisle A2')
        ]
        mock_location_class.get_by_warehouse.return_value = mock_locations
        
        service = WarehouseService()
        result = service.get_warehouse_locations('wh-001')
        
        assert result['success'] is True
        assert len(result['data']) == 2
        assert result['data'][0]['name'] == 'Aisle A1'


class TestTransactionService:
    """Test cases for TransactionService."""
    
    def test_transaction_service_initialization(self):
        """Test TransactionService initialization."""
        service = TransactionService()
        assert isinstance(service, BaseService)
    
    @patch('backend.services.transaction_service.StockTransaction')
    def test_get_all_transactions_success(self, mock_transaction_class):
        """Test successful transactions retrieval."""
        mock_transactions = [
            MagicMock(id='trans-001', transaction_type='IN', quantity_change=100),
            MagicMock(id='trans-002', transaction_type='OUT', quantity_change=-50)
        ]
        mock_transaction_class.get_all.return_value = mock_transactions
        
        service = TransactionService()
        result = service.get_all_transactions()
        
        assert result['success'] is True
        assert len(result['data']) == 2
        assert result['data'][0]['transaction_type'] == 'IN'
    
    @patch('backend.services.transaction_service.StockTransaction')
    def test_create_transaction_success(self, mock_transaction_class):
        """Test successful transaction creation."""
        transaction_data = {
            'stock_item_id': 'stock-001',
            'transaction_type': 'IN',
            'quantity_change': 100,
            'quantity_before': 50,
            'quantity_after': 150,
            'user_id': 'user-001',
            'reference_id': 'REF-001'
        }
        
        mock_transaction_class.create.return_value = 'trans-001'
        
        service = TransactionService()
        result = service.create_transaction(**transaction_data)
        
        assert result['success'] is True
        assert result['data']['id'] == 'trans-001'
        assert result['message'] == "Transaction created successfully"


class TestScannerService:
    """Test cases for ScannerService."""
    
    def test_scanner_service_initialization(self):
        """Test ScannerService initialization."""
        service = ScannerService()
        assert isinstance(service, BaseService)
    
    def test_validate_barcode_format_valid(self):
        """Test valid barcode format validation."""
        service = ScannerService()
        
        # Test valid formats
        assert service.validate_barcode_format('1234567890123') is True  # EAN-13
        assert service.validate_barcode_format('123456789012345678') is True  # EAN-18
        assert service.validate_barcode_format('ABC123') is True  # Alphanumeric
    
    def test_validate_barcode_format_invalid(self):
        """Test invalid barcode format validation."""
        service = ScannerService()
        
        # Test invalid formats
        assert service.validate_barcode_format('') is False  # Empty
        assert service.validate_barcode_format('123') is False  # Too short
        assert service.validate_barcode_format('A' * 50) is False  # Too long
    
    @patch('backend.services.scanner_service.Product')
    def test_search_products_success(self, mock_product_class):
        """Test successful product search."""
        mock_product = MagicMock()
        mock_product.id = 'prod-001'
        mock_product.name = 'Test Product'
        mock_product.sku = 'TEST-001'
        mock_product_class.get_by_sku.return_value = mock_product
        
        service = ScannerService()
        result = service.search_products('TEST-001')
        
        assert result['success'] is True
        assert result['data']['id'] == 'prod-001'
        assert result['data']['name'] == 'Test Product'


class TestSimpleAuthService:
    """Test cases for SimpleAuthService."""
    
    def test_auth_service_initialization(self):
        """Test SimpleAuthService initialization."""
        service = SimpleAuthService()
        assert service is not None
    
    @patch('backend.services.simple_auth_service.User')
    def test_authenticate_user_success(self, mock_user_class):
        """Test successful user authentication."""
        mock_user = MagicMock()
        mock_user.id = 'user-001'
        mock_user.username = 'testuser'
        mock_user.role = 'user'
        
        mock_user_class.get_by_username.return_value = mock_user
        
        service = AuthService()
        result = service.authenticate_user('testuser', 'password123')
        
        assert result['success'] is True
        assert result['data']['id'] == 'user-001'
        assert result['data']['username'] == 'testuser'
    
    @patch('backend.services.simple_auth_service.User')
    def test_authenticate_user_invalid_credentials(self, mock_user_class):
        """Test user authentication with invalid credentials."""
        mock_user_class.get_by_username.return_value = None
        
        service = AuthService()
        result = service.authenticate_user('nonexistent', 'password123')
        
        assert result['success'] is False
        assert "Invalid credentials" in result['error']


class TestServiceOrchestrator:
    """Test cases for ServiceOrchestrator."""
    
    def test_service_orchestrator_initialization(self):
        """Test ServiceOrchestrator initialization."""
        service = ServiceOrchestrator()
        assert isinstance(service, BaseService)
        assert hasattr(service, 'warehouse_service')
        assert hasattr(service, 'product_service')
        assert hasattr(service, 'stock_service')
        assert hasattr(service, 'transaction_service')
        assert hasattr(service, 'scanner_service')
    
    @patch('backend.services.service_orchestrator.StockService')
    @patch('backend.services.service_orchestrator.TransactionService')
    def test_perform_stock_transfer_success(self, mock_transaction_service, mock_stock_service):
        """Test successful stock transfer operation."""
        # Mock the stock service methods
        mock_stock_service_instance = MagicMock()
        mock_stock_service_instance.reserve_stock.return_value = {'success': True}
        mock_stock_service_instance.release_reserved_stock.return_value = {'success': True}
        mock_stock_service.return_value = mock_stock_service_instance
        
        # Mock the transaction service
        mock_transaction_service_instance = MagicMock()
        mock_transaction_service_instance.create_transaction.return_value = {'success': True}
        mock_transaction_service.return_value = mock_transaction_service_instance
        
        service = ServiceOrchestrator()
        result = service.perform_stock_transfer(
            stock_item_id='stock-001',
            to_bin_id='bin-002',
            quantity=50,
            user_id='user-001'
        )
        
        assert result['success'] is True
        assert "Stock transfer completed" in result['message']
    
    def test_perform_stock_transfer_validation_failure(self):
        """Test stock transfer with validation failure."""
        service = ServiceOrchestrator()
        result = service.perform_stock_transfer(
            stock_item_id='stock-001',
            to_bin_id='stock-001',  # Same as stock_item_id - should fail
            quantity=50,
            user_id='user-001'
        )
        
        assert result['success'] is False
        assert "Source and destination must be different" in result['error']
    
    @patch('backend.services.service_orchestrator.WarehouseService')
    @patch('backend.services.service_orchestrator.StockService')
    def test_get_inventory_summary_success(self, mock_stock_service, mock_warehouse_service):
        """Test successful inventory summary retrieval."""
        # Mock warehouse service
        mock_warehouse_service_instance = MagicMock()
        mock_warehouse_service_instance.get_all_warehouses.return_value = {
            'success': True,
            'data': [{'id': 'wh-001', 'name': 'Warehouse 1'}]
        }
        mock_warehouse_service.return_value = mock_warehouse_service_instance
        
        # Mock stock service
        mock_stock_service_instance = MagicMock()
        mock_stock_service_instance.get_stock_levels.return_value = {
            'success': True,
            'data': [{'id': 'stock-001', 'on_hand': 100, 'qty_reserved': 10}]
        }
        mock_stock_service.return_value = mock_stock_service_instance
        
        service = ServiceOrchestrator()
        result = service.get_inventory_summary()
        
        assert result['success'] is True
        assert 'warehouses' in result['data']
        assert 'stock_items' in result['data']
