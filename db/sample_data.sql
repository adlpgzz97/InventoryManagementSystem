-- Comprehensive Sample Data for Inventory Management System
-- This script populates the database with realistic test data including batch tracking features

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
        FOR aisle_letter IN SELECT chr(i) FROM generate_series(65, 70) i LOOP -- A to F
            FOR bin_number IN 1..20 LOOP
                INSERT INTO locations (warehouse_id, aisle, bin) 
                VALUES (warehouse_rec.id, aisle_letter, bin_number::TEXT);
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

-- Create Products with Mixed Batch Tracking
INSERT INTO products (sku, name, description, dimensions, weight, barcode, picture_url, batch_tracked) VALUES 
-- Batch-tracked products (medical, food, chemicals)
('MED-001', 'Sterile Surgical Masks', 'Disposable surgical masks with fluid resistance', '17.5x9.5x0.2 cm', 0.05, '1234567890123', 'https://via.placeholder.com/150x150?text=Surgical+Masks', TRUE),
('MED-002', 'Latex Examination Gloves', 'Powder-free latex gloves for medical use', '24x12x0.1 cm', 0.02, '2345678901234', 'https://via.placeholder.com/150x150?text=Latex+Gloves', TRUE),
('CHEM-001', 'Laboratory Reagent A', 'High-purity chemical reagent for analysis', '5x5x10 cm', 0.25, '3456789012345', 'https://via.placeholder.com/150x150?text=Reagent+A', TRUE),
('FOOD-001', 'Emergency Ration Kit', 'Long-term storage emergency food supply', '25x20x8 cm', 2.5, '4567890123456', 'https://via.placeholder.com/150x150?text=Ration+Kit', TRUE),
('PHARM-001', 'First Aid Antiseptic', 'Topical antiseptic solution for wound care', '8x3x12 cm', 0.15, '5678901234567', 'https://via.placeholder.com/150x150?text=Antiseptic', TRUE),

-- Non-batch-tracked products (tools, electronics, general supplies)
('TOOL-001', 'Digital Multimeter', 'Professional digital multimeter with auto-ranging', '18x9x4 cm', 0.6, '6789012345678', 'https://via.placeholder.com/150x150?text=Multimeter', FALSE),
('TOOL-002', 'Precision Screwdriver Set', 'Complete set of precision screwdrivers', '20x15x3 cm', 0.8, '7890123456789', 'https://via.placeholder.com/150x150?text=Screwdriver+Set', FALSE),
('ELEC-001', 'LED Indicator Light', 'High-brightness LED indicator light panel', '5x5x2 cm', 0.1, '8901234567890', 'https://via.placeholder.com/150x150?text=LED+Light', FALSE),
('ELEC-002', 'Power Supply Module', '12V DC regulated power supply module', '10x6x3 cm', 0.3, '9012345678901', 'https://via.placeholder.com/150x150?text=Power+Supply', FALSE),
('SUPPLY-001', 'Heavy Duty Cable Ties', 'Industrial strength plastic cable ties', '30x2x0.5 cm', 0.02, '0123456789012', 'https://via.placeholder.com/150x150?text=Cable+Ties', FALSE),
('SUPPLY-002', 'Protective Safety Goggles', 'Impact resistant safety goggles', '16x8x6 cm', 0.15, '1234567890124', 'https://via.placeholder.com/150x150?text=Safety+Goggles', FALSE),
('WIDGET-001', 'Premium Widget A', 'High-quality widget for industrial applications', '10x5x2 cm', 0.5, '2345678901235', 'https://via.placeholder.com/150x150?text=Widget+A', FALSE),
('GADGET-001', 'Digital Gadget Pro', 'Advanced digital gadget with smart features', '15x8x3 cm', 0.8, '3456789012346', 'https://via.placeholder.com/150x150?text=Gadget+Pro', FALSE),
('COMPONENT-001', 'Electronic Component Set', 'Essential electronic components for circuits', '12x8x2 cm', 0.3, '4567890123457', 'https://via.placeholder.com/150x150?text=Components', FALSE),
('HARDWARE-001', 'Stainless Steel Bolts', 'M6x20mm stainless steel hex bolts', '2x2x2 cm', 0.05, '5678901234568', 'https://via.placeholder.com/150x150?text=Bolts', FALSE);

-- Create Stock Items with Realistic Batch Information
DO $$
DECLARE
    product_rec RECORD;
    location_rec RECORD;
    warehouse_count INTEGER := 0;
    location_count INTEGER := 0;
    stock_qty INTEGER;
    reserved_qty INTEGER;
    batch_suffix INTEGER := 1;
    admin_user_id UUID;
BEGIN
    -- Get admin user ID for transaction logging
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin' LIMIT 1;
    
    FOR product_rec IN SELECT * FROM products ORDER BY sku LOOP
        warehouse_count := 0;
        
        -- Create stock in 2-3 warehouses per product
        FOR location_rec IN 
            SELECT l.*, w.name as warehouse_name 
            FROM locations l 
            JOIN warehouses w ON l.warehouse_id = w.id 
            WHERE l.aisle IN ('A', 'B') AND l.bin IN ('1', '2', '3')
            ORDER BY RANDOM() 
            LIMIT 2 + (RANDOM() * 2)::INTEGER 
        LOOP
            warehouse_count := warehouse_count + 1;
            
            -- Generate realistic quantities
            stock_qty := CASE 
                WHEN product_rec.batch_tracked THEN 20 + (RANDOM() * 80)::INTEGER
                ELSE 50 + (RANDOM() * 200)::INTEGER
            END;
            
            reserved_qty := CASE 
                WHEN RANDOM() < 0.3 THEN (stock_qty * 0.1 * RANDOM())::INTEGER
                ELSE 0
            END;
            
            IF product_rec.batch_tracked THEN
                -- Create batch-tracked stock using the smart receiving function
                PERFORM handle_stock_receiving(
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
                    admin_user_id
                );
                
                batch_suffix := batch_suffix + 1;
            ELSE
                -- Create non-batch-tracked stock using the smart receiving function
                PERFORM handle_stock_receiving(
                    product_rec.id,
                    location_rec.id,
                    stock_qty,
                    reserved_qty,
                    NULL,
                    NULL,
                    admin_user_id
                );
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- Create some additional batch transactions for history
DO $$
DECLARE
    stock_rec RECORD;
    adjustment_qty INTEGER;
    admin_user_id UUID;
    manager_user_id UUID;
BEGIN
    -- Get user IDs
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin' LIMIT 1;
    SELECT id INTO manager_user_id FROM users WHERE username = 'manager' LIMIT 1;
    
    -- Create some adjustment transactions
    FOR stock_rec IN 
        SELECT * FROM stock_items 
        WHERE qty_available > 20 
        ORDER BY RANDOM() 
        LIMIT 5 
    LOOP
        adjustment_qty := -1 * (1 + (RANDOM() * 5)::INTEGER);
        
        -- Update stock quantity
        UPDATE stock_items 
        SET qty_available = qty_available + adjustment_qty
        WHERE id = stock_rec.id;
        
        -- Log adjustment transaction
        INSERT INTO stock_transactions (
            stock_item_id, transaction_type, quantity_change,
            quantity_before, quantity_after, user_id, notes
        ) VALUES (
            stock_rec.id, 'adjust', adjustment_qty,
            stock_rec.qty_available, stock_rec.qty_available + adjustment_qty,
            CASE WHEN RANDOM() < 0.5 THEN admin_user_id ELSE manager_user_id END,
            'Inventory adjustment - damaged items removed'
        );
    END LOOP;
    
    -- Create some reservation transactions
    FOR stock_rec IN 
        SELECT * FROM stock_items 
        WHERE qty_available > 10 AND qty_reserved = 0
        ORDER BY RANDOM() 
        LIMIT 3 
    LOOP
        adjustment_qty := 5 + (RANDOM() * 10)::INTEGER;
        
        -- Update reservations
        UPDATE stock_items 
        SET qty_reserved = qty_reserved + adjustment_qty,
            qty_available = qty_available - adjustment_qty
        WHERE id = stock_rec.id;
        
        -- Log reservation transaction
        INSERT INTO stock_transactions (
            stock_item_id, transaction_type, quantity_change,
            quantity_before, quantity_after, user_id, notes
        ) VALUES (
            stock_rec.id, 'reserve', -adjustment_qty,
            stock_rec.qty_available, stock_rec.qty_available - adjustment_qty,
            manager_user_id,
            'Stock reserved for customer order'
        );
    END LOOP;
END $$;

-- Create some expiring stock for testing alerts
DO $$
DECLARE
    expiring_stock_id UUID;
    admin_user_id UUID;
BEGIN
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin' LIMIT 1;
    
    -- Get a batch-tracked product for creating expiring stock
    SELECT id INTO expiring_stock_id FROM products WHERE batch_tracked = TRUE LIMIT 1;
    
    IF expiring_stock_id IS NOT NULL THEN
        -- Create stock expiring soon (within 30 days)
        PERFORM handle_stock_receiving(
            expiring_stock_id,
            (SELECT id FROM locations LIMIT 1),
            15,
            0,
            'EXPIRING-BATCH-' || TO_CHAR(NOW(), 'YYYY-MM-DD'),
            CURRENT_DATE + INTERVAL '15 days',  -- Expires in 15 days
            admin_user_id
        );
        
        -- Create stock expiring very soon (within 7 days)
        PERFORM handle_stock_receiving(
            expiring_stock_id,
            (SELECT id FROM locations OFFSET 1 LIMIT 1),
            8,
            0,
            'URGENT-BATCH-' || TO_CHAR(NOW(), 'YYYY-MM-DD'),
            CURRENT_DATE + INTERVAL '5 days',  -- Expires in 5 days
            admin_user_id
        );
    END IF;
END $$;

-- Summary Report
DO $$
DECLARE
    total_products INTEGER;
    total_locations INTEGER;
    total_stock_items INTEGER;
    total_transactions INTEGER;
    batch_tracked_products INTEGER;
    expiring_items INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_products FROM products;
    SELECT COUNT(*) INTO total_locations FROM locations;
    SELECT COUNT(*) INTO total_stock_items FROM stock_items;
    SELECT COUNT(*) INTO total_transactions FROM stock_transactions;
    SELECT COUNT(*) INTO batch_tracked_products FROM products WHERE batch_tracked = TRUE;
    SELECT COUNT(*) INTO expiring_items FROM stock_items WHERE expiry_date <= CURRENT_DATE + INTERVAL '30 days';
    
    RAISE NOTICE 'Sample data population completed!';
    RAISE NOTICE '=====================================';
    RAISE NOTICE 'Products created: %', total_products;
    RAISE NOTICE 'Batch-tracked products: %', batch_tracked_products;
    RAISE NOTICE 'Locations created: %', total_locations;
    RAISE NOTICE 'Stock items created: %', total_stock_items;
    RAISE NOTICE 'Stock transactions logged: %', total_transactions;
    RAISE NOTICE 'Items expiring within 30 days: %', expiring_items;
    RAISE NOTICE '=====================================';
    RAISE NOTICE 'Ready for testing!';
END $$;