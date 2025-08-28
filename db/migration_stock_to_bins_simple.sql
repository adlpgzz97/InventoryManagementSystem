-- Migration: Change stock_items from location_id to bin_id
-- This migration associates stock items with bins instead of locations
-- Bins can move between locations while keeping their contents consistent

BEGIN;

-- Step 1: Add bin_id column to stock_items table
ALTER TABLE stock_items ADD COLUMN bin_id UUID REFERENCES bins(id) ON DELETE CASCADE;

-- Step 2: Create index for better performance
CREATE INDEX idx_stock_items_bin_id ON stock_items(bin_id);

-- Step 3: Populate bin_id for existing stock items
-- Assign each stock item to an available bin
UPDATE stock_items 
SET bin_id = (
    SELECT b.id 
    FROM bins b
    LEFT JOIN stock_items si ON b.id = si.bin_id
    WHERE si.bin_id IS NULL
    LIMIT 1
)
WHERE bin_id IS NULL;

-- Step 4: Create additional bins if needed for remaining stock items
-- This will be handled by the Python script

-- Step 5: Make bin_id NOT NULL after all stock items have been assigned
ALTER TABLE stock_items ALTER COLUMN bin_id SET NOT NULL;

-- Step 6: Remove the old location_id column
ALTER TABLE stock_items DROP COLUMN location_id;

-- Step 7: Create a view to help with queries that need location information
CREATE OR REPLACE VIEW stock_items_with_location AS
SELECT 
    si.id,
    si.product_id,
    si.bin_id,
    si.on_hand,
    si.qty_reserved,
    si.batch_id,
    si.expiry_date,
    si.received_date,
    si.created_at,
    b.code as bin_code,
    l.id as location_id,
    l.full_code as location_code,
    w.id as warehouse_id,
    w.name as warehouse_name
FROM stock_items si
JOIN bins b ON si.bin_id = b.id
LEFT JOIN locations l ON b.location_id = l.id
LEFT JOIN warehouses w ON l.warehouse_id = w.id;

-- Step 8: Create a function to move a bin to a new location
CREATE OR REPLACE FUNCTION move_bin_to_location(
    p_bin_id UUID,
    p_new_location_id UUID
) RETURNS BOOLEAN AS $$
BEGIN
    -- Update the bin's location
    UPDATE bins 
    SET location_id = p_new_location_id, updated_at = NOW()
    WHERE id = p_bin_id;
    
    -- Return true if the update was successful
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Step 9: Create a function to get stock items in a bin
CREATE OR REPLACE FUNCTION get_stock_in_bin(p_bin_code VARCHAR(10))
RETURNS TABLE(
    product_name TEXT,
    sku TEXT,
    on_hand INTEGER,
    qty_reserved INTEGER,
    total_qty INTEGER,
    batch_id TEXT,
    expiry_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.name,
        p.sku,
        si.on_hand,
        si.qty_reserved,
        (si.on_hand + si.qty_reserved) as total_qty,
        si.batch_id,
        si.expiry_date
    FROM stock_items si
    JOIN products p ON si.product_id = p.id
    JOIN bins b ON si.bin_id = b.id
    WHERE b.code = p_bin_code;
END;
$$ LANGUAGE plpgsql;

COMMIT;
