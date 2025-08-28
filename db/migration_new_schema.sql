-- Migration script for new schema implementation
-- Run this script to implement the new schema changes

BEGIN;

-- Step 1: Create new tables
CREATE TABLE IF NOT EXISTS replenishment_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    forecasting_mode TEXT NOT NULL DEFAULT 'automatic' 
        CHECK (forecasting_mode IN ('automatic', 'manual', 'hybrid')),
    manual_reorder_point INTEGER,
    manual_safety_stock INTEGER,
    manual_lead_time_days INTEGER DEFAULT 7,
    forecasting_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(product_id)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    contact_person TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    website TEXT,
    payment_terms TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    supplier_sku TEXT,
    unit_cost NUMERIC,
    lead_time_days INTEGER,
    minimum_order_quantity INTEGER,
    is_preferred BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(product_id, supplier_id)
);

-- Step 2: Migrate existing forecasting data
INSERT INTO replenishment_policies (
    product_id, 
    forecasting_mode, 
    manual_reorder_point, 
    manual_safety_stock, 
    manual_lead_time_days, 
    forecasting_notes
)
SELECT 
    id as product_id,
    COALESCE(forecasting_mode, 'automatic') as forecasting_mode,
    manual_reorder_point,
    manual_safety_stock,
    COALESCE(manual_lead_time_days, 7) as manual_lead_time_days,
    forecasting_notes
FROM products
WHERE forecasting_mode IS NOT NULL 
   OR manual_reorder_point IS NOT NULL 
   OR manual_safety_stock IS NOT NULL 
   OR forecasting_notes IS NOT NULL;

-- Step 3: Create default policies for products without forecasting data
INSERT INTO replenishment_policies (
    product_id, 
    forecasting_mode, 
    manual_lead_time_days
)
SELECT 
    id as product_id,
    'automatic' as forecasting_mode,
    7 as manual_lead_time_days
FROM products p
WHERE NOT EXISTS (
    SELECT 1 FROM replenishment_policies rp WHERE rp.product_id = p.id
);

-- Step 4: Remove forecasting columns from products table
ALTER TABLE products DROP COLUMN IF EXISTS forecasting_mode;
ALTER TABLE products DROP COLUMN IF EXISTS manual_reorder_point;
ALTER TABLE products DROP COLUMN IF EXISTS manual_safety_stock;
ALTER TABLE products DROP COLUMN IF EXISTS manual_lead_time_days;
ALTER TABLE products DROP COLUMN IF EXISTS forecasting_notes;

-- Step 5: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_replenishment_policies_product_id ON replenishment_policies(product_id);
CREATE INDEX IF NOT EXISTS idx_product_suppliers_product_id ON product_suppliers(product_id);
CREATE INDEX IF NOT EXISTS idx_product_suppliers_supplier_id ON product_suppliers(supplier_id);

COMMIT;
