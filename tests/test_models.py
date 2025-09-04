import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from backend.models.user import User
from backend.models.product import Product
from backend.models.stock import StockItem, StockTransaction
from backend.models.warehouse import Warehouse, Location, Bin


class TestUserModel:
    """Test cases for User model."""
    
    def test_user_creation(self, sample_user_data):
        """Test creating a user with valid data."""
        user = User(**sample_user_data)
        
        assert user.id == sample_user_data['id']
        assert user.username == sample_user_data['username']
        assert user.role == sample_user_data['role']
    
    def test_user_from_dict(self, sample_user_data):
        """Test creating user from dictionary."""
        user = User.from_dict(sample_user_data)
        
        assert user.id == sample_user_data['id']
        assert user.username == sample_user_data['username']
        assert user.role == sample_user_data['role']
    
    def test_user_to_dict(self, sample_user_data):
        """Test converting user to dictionary."""
        user = User(**sample_user_data)
        user_dict = user.to_dict()
        
        assert user_dict['id'] == sample_user_data['id']
        assert user_dict['username'] == sample_user_data['username']
        assert user_dict['role'] == sample_user_data['role']
        assert 'is_admin' in user_dict
        assert 'is_manager' in user_dict
        assert 'is_worker' in user_dict
    
    def test_user_role_properties(self, sample_user_data):
        """Test user role computed properties."""
        # Test admin role
        admin_user = User(id='admin-001', username='admin', role='admin')
        assert admin_user.is_admin is True
        assert admin_user.is_manager is False
        assert admin_user.is_worker is False
        
        # Test manager role
        manager_user = User(id='manager-001', username='manager', role='manager')
        assert manager_user.is_admin is False
        assert manager_user.is_manager is True
        assert manager_user.is_worker is False
        
        # Test worker role
        worker_user = User(id='worker-001', username='worker', role='worker')
        assert worker_user.is_admin is False
        assert worker_user.is_manager is False
        assert worker_user.is_worker is True
    
    @patch('backend.models.user.execute_query')
    def test_user_get_by_id(self, mock_execute_query, sample_user_data):
        """Test retrieving user by ID."""
        mock_execute_query.return_value = sample_user_data
        
        user = User.get_by_id('user-001')
        
        assert user is not None
        assert user.id == sample_user_data['id']
        assert user.username == sample_user_data['username']
        mock_execute_query.assert_called_once()
    
    @patch('backend.models.user.execute_query')
    def test_user_get_by_username(self, mock_execute_query, sample_user_data):
        """Test retrieving user by username."""
        mock_execute_query.return_value = sample_user_data
        
        user = User.get_by_username('testuser')
        
        assert user is not None
        assert user.username == sample_user_data['username']
        mock_execute_query.assert_called_once()
    
    @patch('backend.models.user.execute_query')
    def test_user_get_all(self, mock_execute_query, sample_user_data):
        """Test retrieving all users."""
        mock_execute_query.return_value = [sample_user_data, sample_user_data]
        
        users = User.get_all()
        
        assert len(users) == 2
        assert all(isinstance(user, User) for user in users)
        mock_execute_query.assert_called_once()


class TestProductModel:
    """Test cases for Product model."""
    
    def test_product_creation(self, sample_product_data):
        """Test creating a product with valid data."""
        product = Product(**sample_product_data)
        
        assert product.id == sample_product_data['id']
        assert product.name == sample_product_data['name']
        assert product.sku == sample_product_data['sku']
        assert product.description == sample_product_data['description']
        assert product.barcode == sample_product_data['barcode']
        assert product.dimensions == sample_product_data['dimensions']
        assert product.weight == sample_product_data['weight']
        assert product.picture_url == sample_product_data['picture_url']
        assert product.batch_tracked == sample_product_data['batch_tracked']
    
    def test_product_from_dict(self, sample_product_data):
        """Test creating product from dictionary."""
        product = Product.from_dict(sample_product_data)
        
        assert product.id == sample_product_data['id']
        assert product.name == sample_product_data['name']
        assert product.sku == sample_product_data['sku']
    
    def test_product_to_dict(self, sample_product_data):
        """Test converting product to dictionary."""
        product = Product(**sample_product_data)
        product_dict = product.to_dict()
        
        assert product_dict['id'] == sample_product_data['id']
        assert product_dict['name'] == sample_product_data['name']
        assert product_dict['sku'] == sample_product_data['sku']
        assert product_dict['barcode'] == sample_product_data['barcode']
        assert product_dict['dimensions'] == sample_product_data['dimensions']
        assert product_dict['weight'] == sample_product_data['weight']
    
    @patch('backend.models.product.execute_query')
    def test_product_get_by_id(self, mock_execute_query, sample_product_data):
        """Test retrieving product by ID."""
        mock_execute_query.return_value = sample_product_data
        
        product = Product.get_by_id('prod-001')
        
        assert product is not None
        assert product.id == sample_product_data['id']
        assert product.name == sample_product_data['name']
        mock_execute_query.assert_called_once()
    
    @patch('backend.models.product.execute_query')
    def test_product_get_by_sku(self, mock_execute_query, sample_product_data):
        """Test retrieving product by SKU."""
        mock_execute_query.return_value = sample_product_data
        
        product = Product.get_by_sku('TEST-001')
        
        assert product is not None
        assert product.sku == sample_product_data['sku']
        mock_execute_query.assert_called_once()
    
    @patch('backend.models.product.execute_query')
    def test_product_get_all(self, mock_execute_query, sample_product_data):
        """Test retrieving all products."""
        mock_execute_query.return_value = [sample_product_data, sample_product_data]
        
        products = Product.get_all()
        
        assert len(products) == 2
        assert all(isinstance(product, Product) for product in products)
        mock_execute_query.assert_called_once()


class TestStockItemModel:
    """Test cases for StockItem model."""
    
    def test_stock_item_creation(self, sample_stock_data):
        """Test creating a stock item with valid data."""
        stock_item = StockItem(**sample_stock_data)
        
        assert stock_item.id == sample_stock_data['id']
        assert stock_item.product_id == sample_stock_data['product_id']
        assert stock_item.bin_id == sample_stock_data['bin_id']
        assert stock_item.on_hand == sample_stock_data['on_hand']
        assert stock_item.qty_reserved == sample_stock_data['qty_reserved']
        assert stock_item.batch_id == sample_stock_data['batch_id']
        assert stock_item.expiry_date == sample_stock_data['expiry_date']
    
    def test_stock_item_available_stock_property(self, sample_stock_data):
        """Test available_stock property calculation."""
        stock_item = StockItem(**sample_stock_data)
        
        expected_available = sample_stock_data['on_hand'] - sample_stock_data['qty_reserved']
        assert stock_item.available_stock == expected_available
    
    def test_stock_item_from_dict(self, sample_stock_data):
        """Test creating stock item from dictionary."""
        stock_item = StockItem.from_dict(sample_stock_data)
        
        assert stock_item.id == sample_stock_data['id']
        assert stock_item.product_id == sample_stock_data['product_id']
        assert stock_item.on_hand == sample_stock_data['on_hand']
    
    def test_stock_item_to_dict(self, sample_stock_data):
        """Test converting stock item to dictionary."""
        stock_item = StockItem(**sample_stock_data)
        stock_dict = stock_item.to_dict()
        
        assert stock_dict['id'] == sample_stock_data['id']
        assert stock_dict['product_id'] == sample_stock_data['product_id']
        assert stock_dict['on_hand'] == sample_stock_data['on_hand']
        assert stock_dict['reserved'] == sample_stock_data['qty_reserved']
        assert stock_dict['available_stock'] == stock_item.available_stock
    
    @patch('backend.models.stock.execute_query')
    def test_stock_item_get_by_id(self, mock_execute_query, sample_stock_data):
        """Test retrieving stock item by ID."""
        mock_execute_query.return_value = sample_stock_data
        
        stock_item = StockItem.get_by_id('stock-001')
        
        assert stock_item is not None
        assert stock_item.id == sample_stock_data['id']
        assert stock_item.product_id == sample_stock_data['product_id']
        mock_execute_query.assert_called_once()
    
    @patch('backend.models.stock.execute_query')
    def test_stock_item_get_by_batch(self, mock_execute_query, sample_stock_data):
        """Test retrieving stock item by batch number."""
        mock_execute_query.return_value = [sample_stock_data]
        
        stock_items = StockItem.get_by_batch('BATCH-001')
        
        assert len(stock_items) == 1
        assert stock_items[0].batch_id == sample_stock_data['batch_id']
        mock_execute_query.assert_called_once()
    
    @patch('backend.models.stock.execute_query')
    def test_stock_item_get_all(self, mock_execute_query, sample_stock_data):
        """Test retrieving all stock items."""
        mock_execute_query.return_value = [sample_stock_data, sample_stock_data]
        
        stock_items = StockItem.get_all()
        
        assert len(stock_items) == 2
        assert all(isinstance(item, StockItem) for item in stock_items)
        mock_execute_query.assert_called_once()


class TestStockTransactionModel:
    """Test cases for StockTransaction model."""
    
    def test_stock_transaction_creation(self):
        """Test creating a stock transaction with valid data."""
        transaction_data = {
            'id': 'trans-001',
            'transaction_type': 'IN',
            'stock_item_id': 'stock-001',
            'quantity_change': 50,
            'quantity_before': 100,
            'quantity_after': 150,
            'user_id': 'user-001',
            'reference_id': 'REF-001',
            'notes': 'Test transaction'
        }
        
        transaction = StockTransaction(**transaction_data)
        
        assert transaction.id == transaction_data['id']
        assert transaction.transaction_type == transaction_data['transaction_type']
        assert transaction.stock_item_id == transaction_data['stock_item_id']
        assert transaction.quantity_change == transaction_data['quantity_change']
        assert transaction.quantity_before == transaction_data['quantity_before']
        assert transaction.quantity_after == transaction_data['quantity_after']
        assert transaction.user_id == transaction_data['user_id']
        assert transaction.reference_id == transaction_data['reference_id']
    
    def test_stock_transaction_from_dict(self):
        """Test creating stock transaction from dictionary."""
        transaction_data = {
            'id': 'trans-002',
            'transaction_type': 'OUT',
            'stock_item_id': 'stock-001',
            'quantity_change': -25,
            'quantity_before': 150,
            'quantity_after': 125,
            'user_id': 'user-001',
            'reference_id': 'REF-002'
        }
        
        transaction = StockTransaction.from_dict(transaction_data)
        
        assert transaction.id == transaction_data['id']
        assert transaction.transaction_type == transaction_data['transaction_type']
        assert transaction.stock_item_id == transaction_data['stock_item_id']
        assert transaction.quantity_change == transaction_data['quantity_change']
    
    def test_stock_transaction_to_dict(self):
        """Test converting stock transaction to dictionary."""
        transaction_data = {
            'id': 'trans-003',
            'transaction_type': 'IN',
            'stock_item_id': 'stock-001',
            'quantity_change': 100,
            'quantity_before': 125,
            'quantity_after': 225,
            'user_id': 'user-001',
            'reference_id': 'REF-003'
        }
        
        transaction = StockTransaction(**transaction_data)
        transaction_dict = transaction.to_dict()
        
        assert transaction_dict['id'] == transaction_data['id']
        assert transaction_dict['transaction_type'] == transaction_data['transaction_type']
        assert transaction_dict['stock_item_id'] == transaction_data['stock_item_id']
        assert transaction_dict['quantity_change'] == transaction_data['quantity_change']
        assert transaction_dict['user_id'] == transaction_data['user_id']
    
    @patch('backend.models.stock.execute_query')
    def test_stock_transaction_get_by_id(self, mock_execute_query):
        """Test retrieving stock transaction by ID."""
        transaction_data = {
            'id': 'trans-001',
            'transaction_type': 'OUT',
            'stock_item_id': 'stock-001',
            'quantity_change': -25,
            'quantity_before': 150,
            'quantity_after': 125,
            'user_id': 'user-001',
            'reference_id': 'REF-002'
        }
        
        mock_execute_query.return_value = transaction_data
        
        transaction = StockTransaction.get_by_id('trans-001')
        
        assert transaction is not None
        assert transaction.transaction_type == transaction_data['transaction_type']
        mock_execute_query.assert_called_once()
    
    @patch('backend.models.stock.execute_query')
    def test_stock_transaction_get_by_reference(self, mock_execute_query):
        """Test retrieving stock transaction by reference ID."""
        transaction_data = {
            'id': 'trans-003',
            'transaction_type': 'IN',
            'stock_item_id': 'stock-001',
            'quantity_change': 100,
            'quantity_before': 125,
            'quantity_after': 225,
            'user_id': 'user-001',
            'reference_id': 'REF-003'
        }
        
        mock_execute_query.return_value = [transaction_data]
        
        transactions = StockTransaction.get_by_reference('REF-003')
        
        assert len(transactions) == 1
        assert transactions[0].reference_id == transaction_data['reference_id']
        mock_execute_query.assert_called_once()


class TestWarehouseModel:
    """Test cases for Warehouse model."""
    
    def test_warehouse_creation(self, sample_warehouse_data):
        """Test creating a warehouse with valid data."""
        warehouse = Warehouse(**sample_warehouse_data)
        
        assert warehouse.id == sample_warehouse_data['id']
        assert warehouse.name == sample_warehouse_data['name']
        assert warehouse.address == sample_warehouse_data['address']
        assert warehouse.code == sample_warehouse_data['code']
    
    def test_warehouse_from_dict(self, sample_warehouse_data):
        """Test creating warehouse from dictionary."""
        warehouse = Warehouse.from_dict(sample_warehouse_data)
        
        assert warehouse.id == sample_warehouse_data['id']
        assert warehouse.name == sample_warehouse_data['name']
        assert warehouse.address == sample_warehouse_data['address']
    
    def test_warehouse_to_dict(self, sample_warehouse_data):
        """Test converting warehouse to dictionary."""
        warehouse = Warehouse(**sample_warehouse_data)
        warehouse_dict = warehouse.to_dict()
        
        assert warehouse_dict['id'] == sample_warehouse_data['id']
        assert warehouse_dict['name'] == sample_warehouse_data['name']
        assert warehouse_dict['address'] == sample_warehouse_data['address']
        assert warehouse_dict['code'] == sample_warehouse_data['code']
    
    @patch('backend.models.warehouse.execute_query')
    def test_warehouse_get_by_id(self, mock_execute_query, sample_warehouse_data):
        """Test retrieving warehouse by ID."""
        mock_execute_query.return_value = sample_warehouse_data
        
        warehouse = Warehouse.get_by_id('wh-001')
        
        assert warehouse is not None
        assert warehouse.id == sample_warehouse_data['id']
        assert warehouse.name == sample_warehouse_data['name']
        mock_execute_query.assert_called_once()
    
    @patch('backend.models.warehouse.execute_query')
    def test_warehouse_get_all(self, mock_execute_query, sample_warehouse_data):
        """Test retrieving all warehouses."""
        mock_execute_query.return_value = [sample_warehouse_data, sample_warehouse_data]
        
        warehouses = Warehouse.get_all()
        
        assert len(warehouses) == 2
        assert all(isinstance(w, Warehouse) for w in warehouses)
        mock_execute_query.assert_called_once()


class TestLocationModel:
    """Test cases for Location model."""
    
    def test_location_creation(self):
        """Test creating a location with valid data."""
        location_data = {
            'id': 'loc-001',
            'warehouse_id': 'wh-001',
            'code': 'LOC-A1',
            'name': 'Aisle A1',
            'description': 'Main aisle in warehouse'
        }
        
        location = Location(**location_data)
        
        assert location.id == location_data['id']
        assert location.warehouse_id == location_data['warehouse_id']
        assert location.code == location_data['code']
        assert location.name == location_data['name']
        assert location.description == location_data['description']
    
    def test_location_from_dict(self):
        """Test creating location from dictionary."""
        location_data = {
            'id': 'loc-002',
            'warehouse_id': 'wh-001',
            'code': 'LOC-B1',
            'name': 'Aisle B1',
            'description': 'Secondary aisle'
        }
        
        location = Location.from_dict(location_data)
        
        assert location.id == location_data['id']
        assert location.warehouse_id == location_data['warehouse_id']
        assert location.code == location_data['code']
    
    def test_location_to_dict(self):
        """Test converting location to dictionary."""
        location_data = {
            'id': 'loc-003',
            'warehouse_id': 'wh-001',
            'code': 'LOC-C1',
            'name': 'Aisle C1',
            'description': 'Tertiary aisle'
        }
        
        location = Location(**location_data)
        location_dict = location.to_dict()
        
        assert location_dict['id'] == location_data['id']
        assert location_dict['warehouse_id'] == location_data['warehouse_id']
        assert location_dict['code'] == location_data['code']
        assert location_dict['name'] == location_data['name']
    
    @patch('backend.models.warehouse.execute_query')
    def test_location_search(self, mock_execute_query):
        """Test searching locations."""
        location_data = {
            'id': 'loc-004',
            'warehouse_id': 'wh-001',
            'code': 'LOC-E1',
            'name': 'Aisle E1',
            'description': 'Searchable location'
        }
        
        mock_execute_query.return_value = [location_data]
        
        locations = Location.search('E1')
        
        assert len(locations) == 1
        assert locations[0].code == location_data['code']
        mock_execute_query.assert_called_once()


class TestBinModel:
    """Test cases for Bin model."""
    
    def test_bin_creation(self):
        """Test creating a bin with valid data."""
        bin_data = {
            'id': 'bin-001',
            'location_id': 'loc-001',
            'code': 'BIN-001',
            'name': 'Storage Bin 1',
            'description': 'Large storage bin for bulk items'
        }
        
        bin_obj = Bin(**bin_data)
        
        assert bin_obj.id == bin_data['id']
        assert bin_obj.location_id == bin_data['location_id']
        assert bin_obj.code == bin_data['code']
        assert bin_obj.name == bin_data['name']
        assert bin_obj.description == bin_data['description']
    
    def test_bin_from_dict(self):
        """Test creating bin from dictionary."""
        bin_data = {
            'id': 'bin-002',
            'location_id': 'loc-001',
            'code': 'BIN-002',
            'name': 'Storage Bin 2',
            'description': 'Medium storage bin'
        }
        
        bin_obj = Bin.from_dict(bin_data)
        
        assert bin_obj.id == bin_data['id']
        assert bin_obj.location_id == bin_data['location_id']
        assert bin_obj.code == bin_data['code']
    
    def test_bin_to_dict(self):
        """Test converting bin to dictionary."""
        bin_data = {
            'id': 'bin-003',
            'location_id': 'loc-001',
            'code': 'BIN-003',
            'name': 'Storage Bin 3',
            'description': 'Small storage bin'
        }
        
        bin_obj = Bin(**bin_data)
        bin_dict = bin_obj.to_dict()
        
        assert bin_dict['id'] == bin_data['id']
        assert bin_dict['location_id'] == bin_data['location_id']
        assert bin_dict['code'] == bin_data['code']
        assert bin_dict['name'] == bin_data['name']
    
    @patch('backend.models.warehouse.execute_query')
    def test_bin_search(self, mock_execute_query):
        """Test searching bins."""
        bin_data = {
            'id': 'bin-005',
            'location_id': 'loc-001',
            'code': 'BIN-005',
            'name': 'Storage Bin 5',
            'description': 'Searchable bin'
        }
        
        mock_execute_query.return_value = [bin_data]
        
        bins = Bin.search('005')
        
        assert len(bins) == 1
        assert bins[0].code == bin_data['code']
        mock_execute_query.assert_called_once()
