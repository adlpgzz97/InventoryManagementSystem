-- Simple Migration: Implement Hierarchical Location Coding Scheme
-- This script adds the new columns and basic functionality

-- Step 1: Add new columns to locations table
ALTER TABLE locations 
ADD COLUMN warehouse_code VARCHAR(10),
ADD COLUMN area_code VARCHAR(10),
ADD COLUMN rack_code VARCHAR(10),
ADD COLUMN level_number INTEGER,
ADD COLUMN bin_number VARCHAR(10),
ADD COLUMN full_code VARCHAR(50);

-- Step 2: Add code column to warehouses table
ALTER TABLE warehouses ADD COLUMN code VARCHAR(10);

-- Step 3: Update existing warehouse codes
UPDATE warehouses SET code = 'W1' WHERE id = (SELECT id FROM warehouses LIMIT 1);

-- Step 4: Migrate existing data to new format
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

-- Step 5: Generate full codes for existing data
UPDATE locations 
SET full_code = warehouse_code || '-' || area_code || '-' || rack_code || '-L' || level_number || '-' || bin_number
WHERE full_code IS NULL;

-- Step 6: Create indexes for better performance
CREATE INDEX idx_locations_warehouse_code ON locations(warehouse_code);
CREATE INDEX idx_locations_area_code ON locations(area_code);
CREATE INDEX idx_locations_rack_code ON locations(rack_code);
CREATE INDEX idx_locations_full_code ON locations(full_code);

-- Step 7: Make full_code unique
ALTER TABLE locations ADD CONSTRAINT uk_locations_full_code UNIQUE (full_code);

-- Step 8: Create sample hierarchical locations for testing
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
