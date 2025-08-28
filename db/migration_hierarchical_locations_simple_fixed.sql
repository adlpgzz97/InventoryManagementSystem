-- Simple Migration: Implement Hierarchical Location Coding Scheme
-- This handles duplicates properly from the start

-- Step 1: Add new columns to locations table
ALTER TABLE locations ADD COLUMN warehouse_code VARCHAR(10);
ALTER TABLE locations ADD COLUMN area_code VARCHAR(10);
ALTER TABLE locations ADD COLUMN rack_code VARCHAR(10);
ALTER TABLE locations ADD COLUMN level_number INTEGER;
ALTER TABLE locations ADD COLUMN bin_number VARCHAR(10);
ALTER TABLE locations ADD COLUMN full_code VARCHAR(50);

-- Step 2: Add code column to warehouses table
ALTER TABLE warehouses ADD COLUMN code VARCHAR(10);

-- Step 3: Assign warehouse codes based on existing warehouse IDs
UPDATE warehouses SET code = 'W1' WHERE id = (SELECT id FROM warehouses LIMIT 1);
UPDATE warehouses SET code = 'W2' WHERE id = (SELECT id FROM warehouses OFFSET 1 LIMIT 1);
UPDATE warehouses SET code = 'W3' WHERE id = (SELECT id FROM warehouses OFFSET 2 LIMIT 1);
UPDATE warehouses SET code = 'W4' WHERE id = (SELECT id FROM warehouses OFFSET 3 LIMIT 1);
UPDATE warehouses SET code = 'W5' WHERE id = (SELECT id FROM warehouses OFFSET 4 LIMIT 1);
UPDATE warehouses SET code = 'W6' WHERE id = (SELECT id FROM warehouses OFFSET 5 LIMIT 1);

-- Step 4: Migrate existing data with proper warehouse assignment and unique codes
UPDATE locations l
SET 
    warehouse_code = w.code,
    area_code = 'A01',
    rack_code = 'R01',
    level_number = 1,
    bin_number = 'B' || LPAD(l.bin, 2, '0'),
    full_code = w.code || '-A01-R01-L1-B' || LPAD(l.bin, 2, '0')
FROM warehouses w
WHERE l.warehouse_id = w.id AND l.warehouse_code IS NULL;

-- Step 5: Create indexes for better performance
CREATE INDEX idx_locations_warehouse_code ON locations(warehouse_code);
CREATE INDEX idx_locations_area_code ON locations(area_code);
CREATE INDEX idx_locations_rack_code ON locations(rack_code);
CREATE INDEX idx_locations_full_code ON locations(full_code);

-- Step 6: Add unique constraint (should work now since each warehouse has unique codes)
ALTER TABLE locations ADD CONSTRAINT uk_locations_full_code UNIQUE (full_code);

-- Step 7: Create sample hierarchical locations for testing (only for W1)
INSERT INTO locations (warehouse_id, warehouse_code, area_code, rack_code, level_number, bin_number, full_code)
SELECT 
    w.id,
    'W1',
    'A01',
    'R01',
    1,
    'B' || LPAD(generate_series(1, 10)::TEXT, 2, '0'),
    'W1-A01-R01-L1-B' || LPAD(generate_series(1, 10)::TEXT, 2, '0')
FROM warehouses w
WHERE w.code = 'W1'
ON CONFLICT (full_code) DO NOTHING;

INSERT INTO locations (warehouse_id, warehouse_code, area_code, rack_code, level_number, bin_number, full_code)
SELECT 
    w.id,
    'W1',
    'A01',
    'R01',
    2,
    'B' || LPAD(generate_series(1, 10)::TEXT, 2, '0'),
    'W1-A01-R01-L2-B' || LPAD(generate_series(1, 10)::TEXT, 2, '0')
FROM warehouses w
WHERE w.code = 'W1'
ON CONFLICT (full_code) DO NOTHING;

INSERT INTO locations (warehouse_id, warehouse_code, area_code, rack_code, level_number, bin_number, full_code)
SELECT 
    w.id,
    'W1',
    'A01',
    'R02',
    1,
    'B' || LPAD(generate_series(1, 10)::TEXT, 2, '0'),
    'W1-A01-R02-L1-B' || LPAD(generate_series(1, 10)::TEXT, 2, '0')
FROM warehouses w
WHERE w.code = 'W1'
ON CONFLICT (full_code) DO NOTHING;

INSERT INTO locations (warehouse_id, warehouse_code, area_code, rack_code, level_number, bin_number, full_code)
SELECT 
    w.id,
    'W1',
    'A02',
    'R01',
    1,
    'B' || LPAD(generate_series(1, 10)::TEXT, 2, '0'),
    'W1-A02-R01-L1-B' || LPAD(generate_series(1, 10)::TEXT, 2, '0')
FROM warehouses w
WHERE w.code = 'W1'
ON CONFLICT (full_code) DO NOTHING;

COMMIT;
