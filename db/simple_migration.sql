-- Simple Batch Tracking Migration
-- Adds essential batch tracking features to existing database

-- ==================================================
-- 1. ADD BATCH TRACKING TO PRODUCTS TABLE
-- ==================================================

-- Add batch_tracked column to products table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'batch_tracked'
    ) THEN
        ALTER TABLE products ADD COLUMN batch_tracked BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- ==================================================
-- 2. ENHANCE STOCK_ITEMS TABLE FOR BATCH TRACKING
-- ==================================================

-- Add batch_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'stock_items' AND column_name = 'batch_id'
    ) THEN
        ALTER TABLE stock_items ADD COLUMN batch_id TEXT;
    END IF;
END $$;

-- Add expiry_date column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'stock_items' AND column_name = 'expiry_date'
    ) THEN
        ALTER TABLE stock_items ADD COLUMN expiry_date DATE;
    END IF;
END $$;

-- Add received_date column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'stock_items' AND column_name = 'received_date'
    ) THEN
        ALTER TABLE stock_items ADD COLUMN received_date TIMESTAMP DEFAULT NOW();
    END IF;
END $$;

-- ==================================================
-- 3. CREATE STOCK_TRANSACTIONS TABLE
-- ==================================================

CREATE TABLE IF NOT EXISTS stock_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_item_id UUID NOT NULL REFERENCES stock_items(id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('receive', 'ship', 'adjust', 'transfer', 'reserve', 'release')),
    quantity_change INTEGER NOT NULL,
    quantity_before INTEGER NOT NULL,
    quantity_after INTEGER NOT NULL,
    reference_id UUID,
    notes TEXT,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==================================================
-- 4. CREATE INDEXES FOR PERFORMANCE
-- ==================================================

CREATE INDEX IF NOT EXISTS idx_stock_transactions_stock_item_id ON stock_transactions(stock_item_id);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_created_at ON stock_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_type ON stock_transactions(transaction_type);

-- ==================================================
-- 5. UPDATE EXISTING DATA
-- ==================================================

-- Set received_date for existing stock items
UPDATE stock_items 
SET received_date = NOW() 
WHERE received_date IS NULL;

-- Set some existing products as batch tracked for demonstration
UPDATE products SET batch_tracked = TRUE 
WHERE id IN (SELECT id FROM products LIMIT 2);

-- ==================================================
-- MIGRATION COMPLETE
-- ==================================================
