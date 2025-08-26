-- Inventory Management App - PostgreSQL Schema
-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Users (for app authentication and role management)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'worker')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    dimensions TEXT,
    weight NUMERIC,
    picture_url TEXT,
    barcode TEXT,
    batch_tracked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Warehouses
CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    address TEXT
);

-- Locations inside warehouses
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE CASCADE,
    aisle TEXT NOT NULL,
    bin TEXT NOT NULL,
    UNIQUE (warehouse_id, aisle, bin)
);

-- Stock items
CREATE TABLE stock_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    location_id UUID REFERENCES locations(id) ON DELETE CASCADE,
    qty_available INT NOT NULL DEFAULT 0,
    qty_reserved INT NOT NULL DEFAULT 0,
    batch_id TEXT,
    expiry_date DATE,
    received_date TIMESTAMP DEFAULT NOW(),
    CHECK (qty_available >= 0),
    CHECK (qty_reserved >= 0)
);

-- Orders
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID,
    status TEXT NOT NULL CHECK (status IN ('open', 'fulfilled', 'cancelled')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reservations (link orders to stock)
CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    qty INT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('reserved', 'picked', 'cancelled')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Stock transactions for audit trail
CREATE TABLE stock_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_item_id UUID REFERENCES stock_items(id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('receive', 'adjust', 'transfer', 'reserve', 'pick', 'return')),
    quantity_change INT NOT NULL,
    quantity_before INT NOT NULL,
    quantity_after INT NOT NULL,
    reference_id UUID, -- Order ID, transfer ID, etc.
    notes TEXT,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Example function for moving stock
CREATE OR REPLACE FUNCTION move_stock(
    p_stock_id UUID,
    p_new_location UUID,
    p_qty INT
) RETURNS VOID AS $$
BEGIN
    UPDATE stock_items
    SET qty_available = qty_available - p_qty
    WHERE id = p_stock_id AND qty_available >= p_qty;

    INSERT INTO stock_items (product_id, location_id, qty_available, qty_reserved)
    SELECT product_id, p_new_location, p_qty, 0
    FROM stock_items
    WHERE id = p_stock_id;
END;
$$ LANGUAGE plpgsql;

-- Sample data for development
INSERT INTO users (username, password_hash, role) VALUES 
('admin', crypt('admin123', gen_salt('bf')), 'admin'),
('manager', crypt('manager123', gen_salt('bf')), 'manager'),
('worker', crypt('worker123', gen_salt('bf')), 'worker');

INSERT INTO warehouses (name, address) VALUES 
('Main Warehouse', '123 Industrial Blvd, City, State'),
('Secondary Warehouse', '456 Storage Ave, City, State');

INSERT INTO locations (warehouse_id, aisle, bin) VALUES 
((SELECT id FROM warehouses WHERE name = 'Main Warehouse'), 'A', '1'),
((SELECT id FROM warehouses WHERE name = 'Main Warehouse'), 'A', '2'),
((SELECT id FROM warehouses WHERE name = 'Main Warehouse'), 'B', '1'),
((SELECT id FROM warehouses WHERE name = 'Secondary Warehouse'), 'A', '1');

INSERT INTO products (sku, name, description, dimensions, weight, batch_tracked) VALUES 
('SKU001', 'Widget A', 'Standard widget for general use', '10x5x2 cm', 0.15, FALSE),
('SKU002', 'Widget B', 'Premium widget with enhanced features', '12x6x3 cm', 0.25, TRUE),
('SKU003', 'Gadget X', 'Multi-purpose gadget', '8x8x4 cm', 0.30, TRUE);

INSERT INTO stock_items (product_id, location_id, qty_available, qty_reserved, batch_id, expiry_date) VALUES 
((SELECT id FROM products WHERE sku = 'SKU001'), (SELECT id FROM locations WHERE aisle = 'A' AND bin = '1' LIMIT 1), 100, 5, NULL, NULL),
((SELECT id FROM products WHERE sku = 'SKU002'), (SELECT id FROM locations WHERE aisle = 'A' AND bin = '2' LIMIT 1), 50, 0, 'BATCH-2024-001', '2024-12-31'),
((SELECT id FROM products WHERE sku = 'SKU003'), (SELECT id FROM locations WHERE aisle = 'B' AND bin = '1' LIMIT 1), 75, 10, 'BATCH-2024-002', '2025-06-30');
