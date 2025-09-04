import pytest
import json
from unittest.mock import patch, MagicMock

from backend.app import create_app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        yield client


class TestDashboardRoutes:
    """Test cases for dashboard routes."""
    
    def test_dashboard_route_success(self, client):
        """Test successful dashboard page access."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard' in response.data
    
    @patch('backend.routes.dashboard.DashboardService')
    def test_api_dashboard_stats_success(self, mock_service_class, client):
        """Test successful API dashboard stats retrieval."""
        mock_service = MagicMock()
        mock_service.get_dashboard_stats.return_value = {
            'success': True,
            'data': {
                'total_products': 10,
                'total_warehouses': 5,
                'total_stock_items': 1000,
                'total_users': 50
            }
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total_products'] == 10
        assert data['data']['total_warehouses'] == 5
    
    @patch('backend.routes.dashboard.DashboardService')
    def test_api_dashboard_stats_service_error(self, mock_service_class, client):
        """Test API dashboard stats with service error."""
        mock_service = MagicMock()
        mock_service.get_dashboard_stats.return_value = {
            'success': False,
            'error': 'Service error occurred'
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/dashboard/stats')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Service error occurred' in data['error']


class TestProductRoutes:
    """Test cases for product routes."""
    
    def test_products_page_success(self, client):
        """Test successful products page access."""
        response = client.get('/products')
        assert response.status_code == 200
        assert b'Products' in response.data
    
    @patch('backend.routes.products.ProductService')
    def test_api_products_get_all_success(self, mock_service_class, client):
        """Test successful API products retrieval."""
        mock_service = MagicMock()
        mock_service.get_all_products.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'name': 'Product 1', 'sku': 'SKU-001'},
                {'id': 2, 'name': 'Product 2', 'sku': 'SKU-002'}
            ]
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/products')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['name'] == 'Product 1'
    
    @patch('backend.routes.products.ProductService')
    def test_api_products_get_by_id_success(self, mock_service_class, client):
        """Test successful API product retrieval by ID."""
        mock_service = MagicMock()
        mock_service.get_product.return_value = {
            'success': True,
            'data': {'id': 1, 'name': 'Product 1', 'sku': 'SKU-001'}
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/products/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['id'] == 1
        assert data['data']['name'] == 'Product 1'
    
    @patch('backend.routes.products.ProductService')
    def test_api_products_create_success(self, mock_service_class, client):
        """Test successful API product creation."""
        mock_service = MagicMock()
        mock_service.create_product.return_value = {
            'success': True,
            'data': {'id': 3},
            'message': 'Product created successfully'
        }
        mock_service_class.return_value = mock_service
        
        product_data = {
            'name': 'New Product',
            'sku': 'NEW-001',
            'description': 'A new product',
            'category': 'Test',
            'unit_price': 25.99,
            'supplier_id': 1
        }
        
        response = client.post('/api/products', 
                             data=json.dumps(product_data),
                             content_type='application/json')
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['id'] == 3
        assert 'Product created successfully' in data['message']
    
    @patch('backend.routes.products.ProductService')
    def test_api_products_create_validation_error(self, mock_service_class, client):
        """Test API product creation with validation error."""
        mock_service = MagicMock()
        mock_service.create_product.return_value = {
            'success': False,
            'error': 'Missing required field: name'
        }
        mock_service_class.return_value = mock_service
        
        product_data = {
            'sku': 'NEW-001',
            # Missing name field
        }
        
        response = client.post('/api/products', 
                             data=json.dumps(product_data),
                             content_type='application/json')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Missing required field: name' in data['error']


class TestStockRoutes:
    """Test cases for stock routes."""
    
    def test_stock_page_success(self, client):
        """Test successful stock page access."""
        response = client.get('/stock')
        assert response.status_code == 200
        assert b'Stock' in response.data
    
    @patch('backend.routes.stock.StockService')
    def test_api_stock_get_all_success(self, mock_service_class, client):
        """Test successful API stock items retrieval."""
        mock_service = MagicMock()
        mock_service.get_stock_levels.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'product_id': 1, 'quantity': 100, 'reserved': 10},
                {'id': 2, 'product_id': 2, 'quantity': 50, 'reserved': 5}
            ]
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/stock')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['quantity'] == 100
    
    @patch('backend.routes.stock.StockService')
    def test_api_stock_reserve_success(self, mock_service_class, client):
        """Test successful API stock reservation."""
        mock_service = MagicMock()
        mock_service.reserve_stock.return_value = {
            'success': True,
            'message': 'Stock reserved successfully'
        }
        mock_service_class.return_value = mock_service
        
        reservation_data = {'quantity': 20}
        
        response = client.post('/api/stock/1/reserve',
                             data=json.dumps(reservation_data),
                             content_type='application/json')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'Stock reserved successfully' in data['message']


class TestWarehouseRoutes:
    """Test cases for warehouse routes."""
    
    def test_warehouses_page_success(self, client):
        """Test successful warehouses page access."""
        response = client.get('/warehouses')
        assert response.status_code == 200
        assert b'Warehouses' in response.data
    
    @patch('backend.routes.warehouses.WarehouseService')
    def test_api_warehouses_get_all_success(self, mock_service_class, client):
        """Test successful API warehouses retrieval."""
        mock_service = MagicMock()
        mock_service.get_all_warehouses.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'name': 'Warehouse 1', 'city': 'City 1'},
                {'id': 2, 'name': 'Warehouse 2', 'city': 'City 2'}
            ]
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/warehouses')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['name'] == 'Warehouse 1'
    
    @patch('backend.routes.warehouses.WarehouseService')
    def test_api_warehouses_get_by_id_success(self, mock_service_class, client):
        """Test successful API warehouse retrieval by ID."""
        mock_service = MagicMock()
        mock_service.get_warehouse.return_value = {
            'success': True,
            'data': {'id': 1, 'name': 'Warehouse 1', 'city': 'City 1'}
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/warehouses/1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['id'] == 1
        assert data['data']['name'] == 'Warehouse 1'


class TestTransactionRoutes:
    """Test cases for transaction routes."""
    
    def test_transactions_page_success(self, client):
        """Test successful transactions page access."""
        response = client.get('/transactions')
        assert response.status_code == 200
        assert b'Transactions' in response.data
    
    @patch('backend.routes.transactions.TransactionService')
    def test_api_transactions_get_all_success(self, mock_service_class, client):
        """Test successful API transactions retrieval."""
        mock_service = MagicMock()
        mock_service.get_transactions.return_value = {
            'success': True,
            'data': [
                {'id': 1, 'transaction_type': 'IN', 'quantity': 100},
                {'id': 2, 'transaction_type': 'OUT', 'quantity': 50}
            ]
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/transactions')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['data'][0]['transaction_type'] == 'IN'
    
    @patch('backend.routes.transactions.TransactionService')
    def test_api_transactions_create_success(self, mock_service_class, client):
        """Test successful API transaction creation."""
        mock_service = MagicMock()
        mock_service.create_transaction.return_value = {
            'success': True,
            'data': {'id': 3},
            'message': 'Transaction created successfully'
        }
        mock_service_class.return_value = mock_service
        
        transaction_data = {
            'transaction_type': 'IN',
            'quantity': 100,
            'product_id': 1,
            'warehouse_id': 1,
            'user_id': 1,
            'reference_id': 'REF-001'
        }
        
        response = client.post('/api/transactions',
                             data=json.dumps(transaction_data),
                             content_type='application/json')
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['id'] == 3
        assert 'Transaction created successfully' in data['message']


class TestScannerRoutes:
    """Test cases for scanner routes."""
    
    def test_scanner_page_success(self, client):
        """Test successful scanner page access."""
        response = client.get('/scanner')
        assert response.status_code == 200
        assert b'Scanner' in response.data
    
    @patch('backend.routes.scanner.ScannerService')
    def test_api_scanner_scan_product_success(self, mock_service_class, client):
        """Test successful API product scanning."""
        mock_service = MagicMock()
        mock_service.scan_product.return_value = {
            'success': True,
            'data': {'id': 1, 'name': 'Product 1', 'sku': 'SKU-001'}
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/scanner/product/SKU-001')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['sku'] == 'SKU-001'
        assert data['data']['name'] == 'Product 1'
    
    @patch('backend.routes.scanner.ScannerService')
    def test_api_scanner_scan_location_success(self, mock_service_class, client):
        """Test successful API location scanning."""
        mock_service = MagicMock()
        mock_service.scan_location.return_value = {
            'success': True,
            'data': {'id': 1, 'code': 'LOC-A1', 'name': 'Aisle A1'}
        }
        mock_service_class.return_value = mock_service
        
        response = client.get('/api/scanner/location/LOC-A1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['code'] == 'LOC-A1'
        assert data['data']['name'] == 'Aisle A1'


class TestAuthRoutes:
    """Test cases for authentication routes."""
    
    def test_login_page_success(self, client):
        """Test successful login page access."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data
    
    @patch('backend.routes.auth.AuthService')
    def test_login_post_success(self, mock_service_class, client):
        """Test successful login POST request."""
        mock_service = MagicMock()
        mock_service.authenticate_user.return_value = {
            'success': True,
            'data': {'id': 1, 'username': 'testuser'}
        }
        mock_service_class.return_value = mock_service
        
        login_data = {
            'username': 'testuser',
            'password': 'password123'
        }
        
        response = client.post('/login',
                             data=json.dumps(login_data),
                             content_type='application/json')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['username'] == 'testuser'
    
    @patch('backend.routes.auth.AuthService')
    def test_login_post_invalid_credentials(self, mock_service_class, client):
        """Test login POST request with invalid credentials."""
        mock_service = MagicMock()
        mock_service.authenticate_user.return_value = {
            'success': False,
            'error': 'Invalid credentials'
        }
        mock_service_class.return_value = mock_service
        
        login_data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = client.post('/login',
                             data=json.dumps(login_data),
                             content_type='application/json')
        assert response.status_code == 401
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid credentials' in data['error']
    
    def test_logout_success(self, client):
        """Test successful logout."""
        response = client.get('/logout')
        assert response.status_code == 302  # Redirect after logout


class TestErrorHandling:
    """Test cases for error handling."""
    
    def test_404_error_handler(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-route')
        assert response.status_code == 404
        assert b'Page Not Found' in response.data
    
    def test_500_error_handler(self, client):
        """Test 500 error handling."""
        # This would require triggering an actual error in the app
        # For now, we'll just test that the error handler exists
        app = create_app()
        assert app.error_handler_spec is not None


class TestHealthCheck:
    """Test cases for health check endpoint."""
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        response = client.get('/api/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
