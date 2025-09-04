"""
Test configuration for Inventory Management System
Contains test data, database configuration, and SQL statements
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List


def generate_uuid() -> str:
    """Generate a UUID string for testing."""
    return str(uuid.uuid4())


# Test database configuration
TEST_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'inventory_test',
    'user': 'test_user',
    'password': 'test_password'
}

# Sample data that matches the actual schema
SAMPLE_PRODUCT_DATA = {
    'sku': 'TEST-001',
    'name': 'Test Product',
    'description': 'A test product for testing',
    'dimensions': '10x5x2 cm',
    'weight': 0.5,
    'picture_url': 'https://example.com/test.jpg',
    'barcode': '1234567890123',
    'batch_tracked': True
}

SAMPLE_WAREHOUSE_DATA = {
    'name': 'Test Warehouse',
    'address': '123 Test Street, Test City, TC 12345',
    'code': 'WH-001'
}

SAMPLE_LOCATION_DATA = {
    'warehouse_id': None,  # Will be set dynamically
    'full_code': 'A1-B2-C3'
}

SAMPLE_BIN_DATA = {
    'code': 'B001',
    'location_id': None  # Will be set dynamically
}

SAMPLE_STOCK_DATA = {
    'product_id': None,  # Will be set dynamically
    'on_hand': 100,
    'qty_reserved': 0,
    'batch_id': 'BATCH-001',
    'expiry_date': (datetime.now() + timedelta(days=30)).date(),
    'received_date': datetime.now(),
    'bin_id': None  # Will be set dynamically
}

SAMPLE_USER_DATA = {
    'username': 'testuser',
    'password_hash': 'hashed_password_123',
    'role': 'worker'
}

SAMPLE_TRANSACTION_DATA = {
    'stock_item_id': None,  # Will be set dynamically
    'transaction_type': 'receive',
    'quantity_change': 50,
    'quantity_before': 0,
    'quantity_after': 50,
    'reference_id': None,
    'notes': 'Test transaction',
    'user_id': None  # Will be set dynamically
}

# SQL statements for creating test tables
CREATE_TEST_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS products (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        sku TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        dimensions TEXT,
        weight NUMERIC,
        picture_url TEXT,
        barcode TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        batch_tracked BOOLEAN DEFAULT FALSE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS warehouses (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name TEXT NOT NULL,
        address TEXT,
        code VARCHAR(50)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS locations (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        warehouse_id UUID REFERENCES warehouses(id),
        full_code VARCHAR(100)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bins (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        code VARCHAR(50) NOT NULL,
        location_id UUID REFERENCES locations(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_items (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        product_id UUID REFERENCES products(id),
        on_hand INTEGER NOT NULL DEFAULT 0,
        qty_reserved INTEGER NOT NULL DEFAULT 0,
        batch_id TEXT,
        expiry_date DATE,
        received_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        bin_id UUID NOT NULL REFERENCES bins(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        username TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_transactions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        stock_item_id UUID NOT NULL REFERENCES stock_items(id),
        transaction_type TEXT NOT NULL,
        quantity_change INTEGER NOT NULL,
        quantity_before INTEGER NOT NULL,
        quantity_after INTEGER NOT NULL,
        reference_id UUID,
        notes TEXT,
        user_id UUID REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
]

# SQL statements for inserting test data
INSERT_TEST_DATA_SQL = [
    """
    INSERT INTO products (sku, name, description, dimensions, weight, picture_url, barcode, batch_tracked)
    VALUES (%(sku)s, %(name)s, %(description)s, %(dimensions)s, %(weight)s, %(picture_url)s, %(barcode)s, %(batch_tracked)s)
    RETURNING *
    """,
    """
    INSERT INTO warehouses (name, address, code)
    VALUES (%(name)s, %(address)s, %(code)s)
    RETURNING *
    """,
    """
    INSERT INTO locations (warehouse_id, full_code)
    VALUES (%(warehouse_id)s, %(full_code)s)
    RETURNING *
    """,
    """
    INSERT INTO bins (code, location_id)
    VALUES (%(code)s, %(location_id)s)
    RETURNING *
    """,
    """
    INSERT INTO stock_items (product_id, on_hand, qty_reserved, batch_id, expiry_date, received_date, bin_id)
    VALUES (%(product_id)s, %(on_hand)s, %(qty_reserved)s, %(batch_id)s, %(expiry_date)s, %(received_date)s, %(bin_id)s)
    RETURNING *
    """,
    """
    INSERT INTO users (username, password_hash, role)
    VALUES (%(username)s, %(password_hash)s, %(role)s)
    RETURNING *
    """,
    """
    INSERT INTO stock_transactions (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, reference_id, notes, user_id)
    VALUES (%(stock_item_id)s, %(transaction_type)s, %(quantity_change)s, %(quantity_before)s, %(quantity_after)s, %(reference_id)s, %(notes)s, %(user_id)s)
    RETURNING *
    """
]

# SQL statements for cleaning up test tables
CLEANUP_TEST_TABLES_SQL = [
    "DROP TABLE IF EXISTS stock_transactions CASCADE",
    "DROP TABLE IF EXISTS stock_items CASCADE",
    "DROP TABLE IF EXISTS bins CASCADE",
    "DROP TABLE IF EXISTS locations CASCADE",
    "DROP TABLE IF EXISTS users CASCADE",
    "DROP TABLE IF EXISTS warehouses CASCADE",
    "DROP TABLE IF EXISTS products CASCADE"
]
