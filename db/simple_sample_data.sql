-- Simple Sample Data for Inventory Management System
-- Populates the database with basic test data

-- Clear existing data (except users) in correct order due to foreign key constraints
DELETE FROM stock_transactions;
DELETE FROM stock_items;
DELETE FROM products;
DELETE FROM locations;
DELETE FROM warehouses;

-- Create Warehouses
INSERT INTO warehouses (name, address) VALUES 
('Main Distribution Center', '1500 Industrial Parkway, Chicago, IL 60622'),
('East Coast Warehouse', '2750 Atlantic Avenue, Brooklyn, NY 11207'),
('West Coast Facility', '4200 Commerce Drive, Los Angeles, CA 90040'),
('Central Hub', '8900 Distribution Blvd, Dallas, TX 75247'),
('Northern Storage', '1200 Logistics Lane, Minneapolis, MN 55418');

-- Create Locations (Aisles A-F, Bins 1-20 for each warehouse)
DO $$
DECLARE
    warehouse_rec RECORD;
    aisle_letter CHAR(1);
    bin_number INTEGER;
BEGIN
    FOR warehouse_rec IN SELECT id FROM warehouses LOOP
        FOR aisle_letter IN SELECT unnest(ARRAY['A','B','C','D','E','F']) LOOP
            FOR bin_number IN 1..20 LOOP
                INSERT INTO locations (warehouse_id, aisle, bin) 
                VALUES (warehouse_rec.id, aisle_letter, bin_number::TEXT);
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

-- Create Products (mix of batch-tracked and non-batch-tracked)
INSERT INTO products (sku, name, description, dimensions, weight, barcode, batch_tracked) VALUES 
-- Medical supplies (batch tracked)
('MED-001', 'Surgical Mask Pack', 'Disposable surgical masks - 50 pack', '15x10x5 cm', 0.2, '1234567890123', TRUE),
('MED-002', 'Latex Gloves', 'Medical grade latex gloves - Size L', '20x12x8 cm', 0.3, '2345678901234', TRUE),
('MED-003', 'Sterile Gauze', 'Sterile gauze pads - 4x4 inch', '12x8x3 cm', 0.1, '3456789012345', TRUE),

-- Pharmaceutical (batch tracked)
('PHARM-001', 'Pain Relief Tablets', 'Over-the-counter pain relief - 100 tablets', '8x5x3 cm', 0.15, '4567890123456', TRUE),
('PHARM-002', 'Antibacterial Cream', 'Topical antibacterial cream - 30g tube', '10x3x3 cm', 0.05, '5678901234567', TRUE),

-- Food items (batch tracked)
('FOOD-001', 'Emergency Rations', 'Long-term storage emergency food rations', '25x15x10 cm', 2.5, '6789012345678', TRUE),
('FOOD-002', 'Vitamin Supplements', 'Daily multivitamin tablets - 90 count', '8x5x8 cm', 0.3, '7890123456789', TRUE),

-- General supplies (non-batch tracked)
('OFFICE-001', 'Copy Paper', 'Standard 8.5x11 copy paper - 500 sheets', '28x22x5 cm', 2.5, '8901234567890', FALSE),
('OFFICE-002', 'Ballpoint Pens', 'Blue ink ballpoint pens - 12 pack', '15x10x2 cm', 0.2, '9012345678901', FALSE),
('OFFICE-003', 'Notebooks', 'Spiral bound notebooks - 5 pack', '23x18x3 cm', 0.8, '0123456789012', FALSE),

-- Cleaning supplies (non-batch tracked)
('CLEAN-001', 'All-Purpose Cleaner', 'Multi-surface cleaning spray - 32oz', '8x8x25 cm', 1.2, '1123456789012', FALSE),
('CLEAN-002', 'Paper Towels', 'Absorbent paper towels - 8 roll pack', '30x20x15 cm', 3.2, '2234567890123', FALSE),

-- Electronic components (non-batch tracked)
('ELEC-001', 'USB Cables', 'USB-C to USB-A cables - 6ft', '20x15x3 cm', 0.3, '3345678901234', FALSE),
('ELEC-002', 'Power Adapters', 'Universal power adapters - 65W', '12x8x5 cm', 0.8, '4456789012345', FALSE),

-- Chemical supplies (batch tracked)
('CHEM-001', 'Laboratory Ethanol', '95% ethanol for laboratory use - 1L', '10x10x30 cm', 1.0, '5567890123456', TRUE);

-- Create Stock Items with realistic quantities and batch information
DO $$
DECLARE
    product_rec RECORD;
    location_rec RECORD;
    warehouse_count INTEGER := 0;
    stock_qty INTEGER;
    reserved_qty INTEGER;
    batch_suffix INTEGER := 1;
    new_stock_id UUID;
BEGIN
    -- Get first warehouse location for each product
    FOR product_rec IN SELECT * FROM products ORDER BY sku LOOP
        warehouse_count := warehouse_count + 1;
        
        -- Get a location (cycle through warehouses)
        SELECT * INTO location_rec 
        FROM locations l 
        JOIN warehouses w ON l.warehouse_id = w.id 
        WHERE l.aisle = 'A' AND l.bin = '1'
        ORDER BY w.name 
        OFFSET (warehouse_count % 5) 
        LIMIT 1;
        
        -- Generate realistic stock quantities
        CASE 
            WHEN product_rec.sku LIKE 'MED-%' THEN 
                stock_qty := 100 + (RANDOM() * 200)::INTEGER;
                reserved_qty := (RANDOM() * 20)::INTEGER;
            WHEN product_rec.sku LIKE 'PHARM-%' THEN 
                stock_qty := 50 + (RANDOM() * 100)::INTEGER;
                reserved_qty := (RANDOM() * 10)::INTEGER;
            WHEN product_rec.sku LIKE 'FOOD-%' THEN 
                stock_qty := 200 + (RANDOM() * 300)::INTEGER;
                reserved_qty := (RANDOM() * 30)::INTEGER;
            WHEN product_rec.sku LIKE 'OFFICE-%' THEN 
                stock_qty := 500 + (RANDOM() * 1000)::INTEGER;
                reserved_qty := (RANDOM() * 50)::INTEGER;
            WHEN product_rec.sku LIKE 'CLEAN-%' THEN 
                stock_qty := 75 + (RANDOM() * 150)::INTEGER;
                reserved_qty := (RANDOM() * 15)::INTEGER;
            WHEN product_rec.sku LIKE 'ELEC-%' THEN 
                stock_qty := 150 + (RANDOM() * 300)::INTEGER;
                reserved_qty := (RANDOM() * 25)::INTEGER;
            WHEN product_rec.sku LIKE 'CHEM-%' THEN 
                stock_qty := 25 + (RANDOM() * 75)::INTEGER;
                reserved_qty := (RANDOM() * 5)::INTEGER;
            ELSE 
                stock_qty := 100 + (RANDOM() * 200)::INTEGER;
                reserved_qty := (RANDOM() * 20)::INTEGER;
        END CASE;
        
        -- Insert stock item
        IF product_rec.batch_tracked THEN
            -- For batch-tracked products, create with batch information
            INSERT INTO stock_items (
                product_id, location_id, qty_available, qty_reserved, 
                batch_id, expiry_date, received_date
            ) VALUES (
                product_rec.id,
                location_rec.id,
                stock_qty,
                reserved_qty,
                product_rec.sku || '-BATCH-' || TO_CHAR(NOW() - (batch_suffix * INTERVAL '1 day'), 'YYYY-MM-DD'),
                CASE
                    WHEN product_rec.sku LIKE 'MED-%' THEN CURRENT_DATE + INTERVAL '2 years'
                    WHEN product_rec.sku LIKE 'FOOD-%' THEN CURRENT_DATE + INTERVAL '5 years'
                    WHEN product_rec.sku LIKE 'CHEM-%' THEN CURRENT_DATE + INTERVAL '1 year'
                    WHEN product_rec.sku LIKE 'PHARM-%' THEN CURRENT_DATE + INTERVAL '18 months'
                    ELSE CURRENT_DATE + INTERVAL '3 years'
                END,
                NOW() - (batch_suffix * INTERVAL '1 day')
            ) RETURNING id INTO new_stock_id;
        ELSE
            -- For non-batch-tracked products
            INSERT INTO stock_items (
                product_id, location_id, qty_available, qty_reserved, received_date
            ) VALUES (
                product_rec.id,
                location_rec.id,
                stock_qty,
                reserved_qty,
                NOW() - (batch_suffix * INTERVAL '1 day')
            ) RETURNING id INTO new_stock_id;
        END IF;
        
        -- Create initial transaction record
        INSERT INTO stock_transactions (
            stock_item_id, transaction_type, quantity_change, 
            quantity_before, quantity_after, notes,
            user_id, created_at
        ) VALUES (
            new_stock_id,
            'receive',
            stock_qty,
            0,
            stock_qty,
            'Initial stock receipt',
            (SELECT id FROM users WHERE role = 'admin' LIMIT 1),
            NOW() - (batch_suffix * INTERVAL '1 day')
        );
        
        batch_suffix := batch_suffix + 1;
    END LOOP;
END $$;

-- Add some additional stock items for variety (multiple locations for same products)
DO $$
DECLARE
    product_rec RECORD;
    location_rec RECORD;
    counter INTEGER := 0;
    new_stock_id UUID;
BEGIN
    -- Add stock for first 5 products in different locations
    FOR product_rec IN SELECT * FROM products ORDER BY sku LIMIT 5 LOOP
        counter := counter + 1;
        
        -- Get a different location (Aisle B)
        SELECT * INTO location_rec 
        FROM locations l 
        JOIN warehouses w ON l.warehouse_id = w.id 
        WHERE l.aisle = 'B' AND l.bin = (counter + 2)::TEXT
        LIMIT 1;
        
        IF location_rec.id IS NOT NULL THEN
            IF product_rec.batch_tracked THEN
                -- Different batch for batch-tracked products
                INSERT INTO stock_items (
                    product_id, location_id, qty_available, qty_reserved, 
                    batch_id, expiry_date, received_date
                ) VALUES (
                    product_rec.id,
                    location_rec.id,
                    50 + (RANDOM() * 100)::INTEGER,
                    0,
                    product_rec.sku || '-BATCH-' || TO_CHAR(NOW() - (counter * 7 * INTERVAL '1 day'), 'YYYY-MM-DD'),
                    CASE
                        WHEN product_rec.sku LIKE 'MED-%' THEN CURRENT_DATE + INTERVAL '2 years'
                        WHEN product_rec.sku LIKE 'FOOD-%' THEN CURRENT_DATE + INTERVAL '5 years'
                        WHEN product_rec.sku LIKE 'CHEM-%' THEN CURRENT_DATE + INTERVAL '1 year'
                        WHEN product_rec.sku LIKE 'PHARM-%' THEN CURRENT_DATE + INTERVAL '18 months'
                        ELSE CURRENT_DATE + INTERVAL '3 years'
                    END,
                    NOW() - (counter * 7 * INTERVAL '1 day')
                ) RETURNING id INTO new_stock_id;
            ELSE
                -- For non-batch products, this would typically combine quantities
                -- But for demo purposes, we'll create separate records
                INSERT INTO stock_items (
                    product_id, location_id, qty_available, qty_reserved, received_date
                ) VALUES (
                    product_rec.id,
                    location_rec.id,
                    75 + (RANDOM() * 150)::INTEGER,
                    0,
                    NOW() - (counter * 7 * INTERVAL '1 day')
                ) RETURNING id INTO new_stock_id;
            END IF;
            
            -- Create transaction record
            INSERT INTO stock_transactions (
                stock_item_id, transaction_type, quantity_change, 
                quantity_before, quantity_after, notes,
                user_id, created_at
            ) VALUES (
                new_stock_id,
                'receive',
                (SELECT qty_available FROM stock_items WHERE id = new_stock_id),
                0,
                (SELECT qty_available FROM stock_items WHERE id = new_stock_id),
                'Additional stock receipt',
                (SELECT id FROM users WHERE role = 'manager' LIMIT 1),
                NOW() - (counter * 7 * INTERVAL '1 day')
            );
        END IF;
    END LOOP;
END $$;
