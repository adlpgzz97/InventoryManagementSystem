-- Migration: Implement Hierarchical Location Coding Scheme
-- Warehouse → Storage Area → Rack → Level → Bin
-- Format: [WH]-[AREA]-[RACK]-[LEVEL]-[BIN]
-- Example: W1-A03-R12-L2-B05

-- Step 1: Add new columns to locations table
ALTER TABLE locations 
ADD COLUMN warehouse_code VARCHAR(10),
ADD COLUMN area_code VARCHAR(10),
ADD COLUMN rack_code VARCHAR(10),
ADD COLUMN level_number INTEGER,
ADD COLUMN bin_number VARCHAR(10),
ADD COLUMN full_code VARCHAR(50);

-- Step 2: Create indexes for better performance (after columns exist)
CREATE INDEX idx_locations_warehouse_code ON locations(warehouse_code);
CREATE INDEX idx_locations_area_code ON locations(area_code);
CREATE INDEX idx_locations_rack_code ON locations(rack_code);
CREATE INDEX idx_locations_full_code ON locations(full_code);

-- Step 3: Create a function to generate full location codes
CREATE OR REPLACE FUNCTION generate_location_code(
    p_warehouse_code VARCHAR(10),
    p_area_code VARCHAR(10),
    p_rack_code VARCHAR(10),
    p_level_number INTEGER,
    p_bin_number VARCHAR(10)
) RETURNS VARCHAR(50) AS $$
BEGIN
    RETURN p_warehouse_code || '-' || 
           p_area_code || '-' || 
           p_rack_code || '-' || 
           'L' || p_level_number || '-' || 
           p_bin_number;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Create a function to validate location codes
CREATE OR REPLACE FUNCTION validate_location_code(
    p_warehouse_code VARCHAR(10),
    p_area_code VARCHAR(10),
    p_rack_code VARCHAR(10),
    p_level_number INTEGER,
    p_bin_number VARCHAR(10)
) RETURNS BOOLEAN AS $$
BEGIN
    -- Validate warehouse code (W1, W2, W3, etc.)
    IF p_warehouse_code !~ '^W[1-9][0-9]*$' THEN
        RETURN FALSE;
    END IF;
    
    -- Validate area code (A01, A02, etc. - 2-3 digits)
    IF p_area_code !~ '^A[0-9]{2,3}$' THEN
        RETURN FALSE;
    END IF;
    
    -- Validate rack code (R01-R99)
    IF p_rack_code !~ '^R[0-9]{2}$' THEN
        RETURN FALSE;
    END IF;
    
    -- Validate level (1-9)
    IF p_level_number < 1 OR p_level_number > 9 THEN
        RETURN FALSE;
    END IF;
    
    -- Validate bin number (B01, B02, etc. - always 2 digits)
    IF p_bin_number !~ '^B[0-9]{2}$' THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create a trigger to automatically generate full_code
CREATE OR REPLACE FUNCTION update_location_full_code()
RETURNS TRIGGER AS $$
BEGIN
    -- Generate full code if all components are provided
    IF NEW.warehouse_code IS NOT NULL AND 
       NEW.area_code IS NOT NULL AND 
       NEW.rack_code IS NOT NULL AND 
       NEW.level_number IS NOT NULL AND 
       NEW.bin_number IS NOT NULL THEN
        
        NEW.full_code = generate_location_code(
            NEW.warehouse_code,
            NEW.area_code,
            NEW.rack_code,
            NEW.level_number,
            NEW.bin_number
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_location_full_code
    BEFORE INSERT OR UPDATE ON locations
    FOR EACH ROW
    EXECUTE FUNCTION update_location_full_code();

-- Step 6: Migrate existing data to new format
-- This will convert existing A1, B2 format to new hierarchical format
UPDATE locations 
SET 
    warehouse_code = 'W1',
    area_code = 'A01',
    rack_code = 'R01',
    level_number = 1,
    bin_number = CASE 
        WHEN aisle = 'A' THEN 'B' || LPAD(bin, 2, '0')
        WHEN aisle = 'B' THEN 'B' || LPAD(bin, 2, '0')
        WHEN aisle = 'C' THEN 'B' || LPAD(bin, 2, '0')
        ELSE 'B' || LPAD(bin, 2, '0')
    END
WHERE warehouse_code IS NULL;

-- Step 7: Add constraints to ensure data integrity
ALTER TABLE locations 
ADD CONSTRAINT chk_warehouse_code CHECK (warehouse_code ~ '^W[1-9][0-9]*$'),
ADD CONSTRAINT chk_area_code CHECK (area_code ~ '^A[0-9]{2,3}$'),
ADD CONSTRAINT chk_rack_code CHECK (rack_code ~ '^R[0-9]{2}$'),
ADD CONSTRAINT chk_level_number CHECK (level_number >= 1 AND level_number <= 9),
ADD CONSTRAINT chk_bin_number CHECK (bin_number ~ '^B[0-9]{2}$'),
ADD CONSTRAINT chk_full_code CHECK (full_code ~ '^W[1-9][0-9]*-A[0-9]{2,3}-R[0-9]{2}-L[1-9]-B[0-9]{2}$');

-- Step 8: Make full_code unique
ALTER TABLE locations ADD CONSTRAINT uk_locations_full_code UNIQUE (full_code);

-- Step 9: Create helper functions for location management
CREATE OR REPLACE FUNCTION create_location_hierarchy(
    p_warehouse_code VARCHAR(10),
    p_area_code VARCHAR(10),
    p_rack_code VARCHAR(10),
    p_level_number INTEGER,
    p_start_bin INTEGER,
    p_end_bin INTEGER
) RETURNS INTEGER AS $$
DECLARE
    v_bin_num INTEGER;
    v_bin_code VARCHAR(10);
    v_count INTEGER := 0;
    v_warehouse_id UUID;
BEGIN
    -- Get warehouse ID
    SELECT id INTO v_warehouse_id FROM warehouses WHERE code = p_warehouse_code LIMIT 1;
    
    IF v_warehouse_id IS NULL THEN
        RAISE EXCEPTION 'Warehouse with code % not found', p_warehouse_code;
    END IF;
    
    -- Validate input
    IF NOT validate_location_code(p_warehouse_code, p_area_code, p_rack_code, p_level_number, 'B01') THEN
        RAISE EXCEPTION 'Invalid location code parameters';
    END IF;
    
    -- Create locations for each bin
    FOR v_bin_num IN p_start_bin..p_end_bin LOOP
        v_bin_code := 'B' || LPAD(v_bin_num::TEXT, 2, '0');
        
        INSERT INTO locations (warehouse_id, warehouse_code, area_code, rack_code, level_number, bin_number)
        VALUES (v_warehouse_id, p_warehouse_code, p_area_code, p_rack_code, p_level_number, v_bin_code)
        ON CONFLICT (full_code) DO NOTHING;
        
        v_count := v_count + 1;
    END LOOP;
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Step 10: Add code column to warehouses table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'warehouses' AND column_name = 'code') THEN
        ALTER TABLE warehouses ADD COLUMN code VARCHAR(10);
        UPDATE warehouses SET code = 'W1' WHERE id = (SELECT id FROM warehouses LIMIT 1);
    END IF;
END $$;

-- Step 11: Create a view for easier location queries
CREATE OR REPLACE VIEW location_hierarchy AS
SELECT 
    l.id,
    l.warehouse_id,
    l.warehouse_code,
    l.area_code,
    l.rack_code,
    l.level_number,
    l.bin_number,
    l.full_code,
    w.name as warehouse_name,
    w.address as warehouse_address,
    CASE 
        WHEN si.id IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END as is_occupied,
    COUNT(si.id) as stock_items_count
FROM locations l
LEFT JOIN warehouses w ON l.warehouse_id = w.id
LEFT JOIN stock_items si ON l.id = si.location_id
GROUP BY l.id, l.warehouse_id, l.warehouse_code, l.area_code, l.rack_code, 
         l.level_number, l.bin_number, l.full_code, w.name, w.address, si.id;

-- Step 12: Create function to get location by full code
CREATE OR REPLACE FUNCTION get_location_by_code(p_full_code VARCHAR(50))
RETURNS TABLE(
    id UUID,
    warehouse_id UUID,
    warehouse_code VARCHAR(10),
    area_code VARCHAR(10),
    rack_code VARCHAR(10),
    level_number INTEGER,
    bin_number VARCHAR(10),
    full_code VARCHAR(50),
    warehouse_name TEXT,
    warehouse_address TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.id,
        l.warehouse_id,
        l.warehouse_code,
        l.area_code,
        l.rack_code,
        l.level_number,
        l.bin_number,
        l.full_code,
        w.name,
        w.address
    FROM locations l
    LEFT JOIN warehouses w ON l.warehouse_id = w.id
    WHERE l.full_code = p_full_code;
END;
$$ LANGUAGE plpgsql;

-- Step 13: Create function to get stock items at location
CREATE OR REPLACE FUNCTION get_stock_items_at_location(p_full_code VARCHAR(50))
RETURNS TABLE(
    id UUID,
    product_name TEXT,
    sku VARCHAR(50),
    barcode VARCHAR(50),
    qty_available INTEGER,
    qty_reserved INTEGER,
    total_qty INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        si.id,
        p.name,
        p.sku,
        p.barcode,
        si.qty_available,
        si.qty_reserved,
        (si.qty_available + si.qty_reserved) as total_qty
    FROM stock_items si
    JOIN products p ON si.product_id = p.id
    JOIN locations l ON si.location_id = l.id
    WHERE l.full_code = p_full_code;
END;
$$ LANGUAGE plpgsql;

-- Step 14: Update existing warehouse codes
UPDATE warehouses SET code = 'W1' WHERE id = (SELECT id FROM warehouses LIMIT 1);

-- Step 15: Create sample hierarchical locations for testing
-- Warehouse 1, Area A01, Rack R01, Level 1, Bins 01-10
SELECT create_location_hierarchy('W1', 'A01', 'R01', 1, 1, 10);

-- Warehouse 1, Area A01, Rack R01, Level 2, Bins 01-10
SELECT create_location_hierarchy('W1', 'A01', 'R01', 2, 1, 10);

-- Warehouse 1, Area A01, Rack R02, Level 1, Bins 01-10
SELECT create_location_hierarchy('W1', 'A01', 'R02', 1, 1, 10);

-- Warehouse 1, Area A02, Rack R01, Level 1, Bins 01-10
SELECT create_location_hierarchy('W1', 'A02', 'R01', 1, 1, 10);

COMMIT;
