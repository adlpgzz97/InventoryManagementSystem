-- Step 1: Add new columns one by one
ALTER TABLE locations ADD COLUMN warehouse_code VARCHAR(10);
ALTER TABLE locations ADD COLUMN area_code VARCHAR(10);
ALTER TABLE locations ADD COLUMN rack_code VARCHAR(10);
ALTER TABLE locations ADD COLUMN level_number INTEGER;
ALTER TABLE locations ADD COLUMN bin_number VARCHAR(10);
ALTER TABLE locations ADD COLUMN full_code VARCHAR(50);

-- Step 2: Add code column to warehouses
ALTER TABLE warehouses ADD COLUMN code VARCHAR(10);

-- Step 3: Set warehouse code
UPDATE warehouses SET code = 'W1' WHERE id = (SELECT id FROM warehouses LIMIT 1);

-- Step 4: Migrate existing data
UPDATE locations 
SET 
    warehouse_code = 'W1',
    area_code = 'A01',
    rack_code = 'R01',
    level_number = 1,
    bin_number = 'B' || LPAD(bin, 2, '0')
WHERE warehouse_code IS NULL;

-- Step 5: Generate full codes
UPDATE locations 
SET full_code = warehouse_code || '-' || area_code || '-' || rack_code || '-L' || level_number || '-' || bin_number
WHERE full_code IS NULL;

-- Step 6: Create indexes
CREATE INDEX idx_locations_warehouse_code ON locations(warehouse_code);
CREATE INDEX idx_locations_area_code ON locations(area_code);
CREATE INDEX idx_locations_rack_code ON locations(rack_code);
CREATE INDEX idx_locations_full_code ON locations(full_code);

-- Step 7: Add unique constraint
ALTER TABLE locations ADD CONSTRAINT uk_locations_full_code UNIQUE (full_code);
