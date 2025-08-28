-- Rollback script for new schema implementation
-- Use this if you need to revert the changes

BEGIN;

-- Step 1: Add forecasting columns back to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS forecasting_mode TEXT DEFAULT 'automatic';
ALTER TABLE products ADD COLUMN IF NOT EXISTS manual_reorder_point INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS manual_safety_stock INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS manual_lead_time_days INTEGER DEFAULT 7;
ALTER TABLE products ADD COLUMN IF NOT EXISTS forecasting_notes TEXT;

-- Step 2: Migrate data back from replenishment_policies
UPDATE products p
SET 
    forecasting_mode = rp.forecasting_mode,
    manual_reorder_point = rp.manual_reorder_point,
    manual_safety_stock = rp.manual_safety_stock,
    manual_lead_time_days = rp.manual_lead_time_days,
    forecasting_notes = rp.forecasting_notes
FROM replenishment_policies rp
WHERE p.id = rp.product_id;

-- Step 3: Drop new tables
DROP TABLE IF EXISTS product_suppliers;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS replenishment_policies;

COMMIT;
