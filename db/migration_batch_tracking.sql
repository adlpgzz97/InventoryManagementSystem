-- Migration script to add batch tracking and audit trail features
-- Run this script to update your existing database schema

-- Add batch_tracked column to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS batch_tracked BOOLEAN DEFAULT FALSE;

-- Add missing columns to stock_items table
ALTER TABLE stock_items ADD COLUMN IF NOT EXISTS batch_id TEXT;
ALTER TABLE stock_items ADD COLUMN IF NOT EXISTS expiry_date DATE;
ALTER TABLE stock_items ADD COLUMN IF NOT EXISTS received_date TIMESTAMP DEFAULT NOW();
ALTER TABLE stock_items ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();

-- Create stock_transactions table for audit trail
CREATE TABLE IF NOT EXISTS stock_transactions (
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stock_items_product_id ON stock_items(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_items_location_id ON stock_items(location_id);
CREATE INDEX IF NOT EXISTS idx_stock_items_batch_id ON stock_items(batch_id);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_stock_item_id ON stock_transactions(stock_item_id);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_created_at ON stock_transactions(created_at);

-- Update existing products to have batch_tracked = false by default
UPDATE products SET batch_tracked = FALSE WHERE batch_tracked IS NULL;

-- Add some sample batch-tracked products for testing
INSERT INTO products (sku, name, description, dimensions, weight, batch_tracked) VALUES 
('SKU004', 'Batch Product A', 'Product with batch tracking', '15x10x5 cm', 0.5, TRUE),
('SKU005', 'Batch Product B', 'Another batch tracked product', '20x15x8 cm', 0.8, TRUE)
ON CONFLICT (sku) DO NOTHING;

-- Add sample stock items with batch tracking
INSERT INTO stock_items (product_id, location_id, qty_available, qty_reserved, batch_id, expiry_date) 
SELECT 
    p.id,
    l.id,
    25,
    0,
    'BATCH-2024-003',
    '2024-12-31'
FROM products p, locations l 
WHERE p.sku = 'SKU004' AND l.aisle = 'A' AND l.bin = '1'
LIMIT 1
ON CONFLICT DO NOTHING;

INSERT INTO stock_items (product_id, location_id, qty_available, qty_reserved, batch_id, expiry_date) 
SELECT 
    p.id,
    l.id,
    30,
    5,
    'BATCH-2024-004',
    '2025-03-15'
FROM products p, locations l 
WHERE p.sku = 'SKU005' AND l.aisle = 'B' AND l.bin = '1'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Verify the migration
SELECT 'Migration completed successfully' as status;
