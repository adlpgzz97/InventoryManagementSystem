-- Migration script to add hybrid forecasting fields to products table
-- This enables both automatic and manual reorder point/safety stock calculation

-- ==================================================
-- 1. ADD FORECASTING FIELDS TO PRODUCTS TABLE
-- ==================================================

-- Add forecasting calculation mode
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'forecasting_mode'
    ) THEN
        ALTER TABLE products ADD COLUMN forecasting_mode TEXT DEFAULT 'automatic' 
        CHECK (forecasting_mode IN ('automatic', 'manual', 'hybrid'));
    END IF;
END $$;

-- Add manual reorder point field
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'manual_reorder_point'
    ) THEN
        ALTER TABLE products ADD COLUMN manual_reorder_point INTEGER DEFAULT NULL;
    END IF;
END $$;

-- Add manual safety stock field
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'manual_safety_stock'
    ) THEN
        ALTER TABLE products ADD COLUMN manual_safety_stock INTEGER DEFAULT NULL;
    END IF;
END $$;

-- Add manual lead time field (in days)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'manual_lead_time_days'
    ) THEN
        ALTER TABLE products ADD COLUMN manual_lead_time_days INTEGER DEFAULT 7;
    END IF;
END $$;

-- Add forecasting notes field
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'products' AND column_name = 'forecasting_notes'
    ) THEN
        ALTER TABLE products ADD COLUMN forecasting_notes TEXT DEFAULT NULL;
    END IF;
END $$;

-- ==================================================
-- 2. CREATE INDEXES FOR PERFORMANCE
-- ==================================================

CREATE INDEX IF NOT EXISTS idx_products_forecasting_mode ON products(forecasting_mode);
CREATE INDEX IF NOT EXISTS idx_products_manual_reorder_point ON products(manual_reorder_point);
CREATE INDEX IF NOT EXISTS idx_products_manual_safety_stock ON products(manual_safety_stock);

-- ==================================================
-- 3. UPDATE EXISTING DATA
-- ==================================================

-- Set all existing products to automatic mode by default
UPDATE products 
SET forecasting_mode = 'automatic' 
WHERE forecasting_mode IS NULL;

-- Set default lead time for existing products
UPDATE products 
SET manual_lead_time_days = 7 
WHERE manual_lead_time_days IS NULL;

-- ==================================================
-- 4. CREATE HELPER FUNCTION FOR FORECASTING CALCULATION
-- ==================================================

CREATE OR REPLACE FUNCTION calculate_product_forecasting(
    p_product_id UUID,
    p_avg_daily_usage NUMERIC DEFAULT 0,
    p_usage_std_dev NUMERIC DEFAULT 0
) RETURNS TABLE(
    reorder_point INTEGER,
    safety_stock INTEGER,
    lead_time_days INTEGER,
    calculation_mode TEXT
) AS $$
DECLARE
    product_rec RECORD;
    calculated_safety_stock INTEGER;
    calculated_reorder_point INTEGER;
BEGIN
    -- Get product forecasting settings
    SELECT 
        forecasting_mode,
        manual_reorder_point,
        manual_safety_stock,
        manual_lead_time_days
    INTO product_rec
    FROM products 
    WHERE id = p_product_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Product not found';
    END IF;
    
    -- Calculate based on forecasting mode
    CASE product_rec.forecasting_mode
        WHEN 'automatic' THEN
            -- Automatic calculation
            calculated_safety_stock := GREATEST(
                ROUND(p_usage_std_dev * 2), 
                ROUND(p_avg_daily_usage * 0.5)
            );
            calculated_reorder_point := ROUND((p_avg_daily_usage * product_rec.manual_lead_time_days) + calculated_safety_stock);
            
            RETURN QUERY SELECT 
                calculated_reorder_point::INTEGER,
                calculated_safety_stock::INTEGER,
                product_rec.manual_lead_time_days::INTEGER,
                'automatic'::TEXT;
                
        WHEN 'manual' THEN
            -- Manual values only
            RETURN QUERY SELECT 
                COALESCE(product_rec.manual_reorder_point, 0)::INTEGER,
                COALESCE(product_rec.manual_safety_stock, 0)::INTEGER,
                product_rec.manual_lead_time_days::INTEGER,
                'manual'::TEXT;
                
        WHEN 'hybrid' THEN
            -- Use manual values if available, otherwise calculate automatically
            calculated_safety_stock := COALESCE(
                product_rec.manual_safety_stock,
                GREATEST(ROUND(p_usage_std_dev * 2), ROUND(p_avg_daily_usage * 0.5))
            );
            calculated_reorder_point := COALESCE(
                product_rec.manual_reorder_point,
                ROUND((p_avg_daily_usage * product_rec.manual_lead_time_days) + calculated_safety_stock)
            );
            
            RETURN QUERY SELECT 
                calculated_reorder_point::INTEGER,
                calculated_safety_stock::INTEGER,
                product_rec.manual_lead_time_days::INTEGER,
                'hybrid'::TEXT;
                
        ELSE
            -- Default to automatic
            calculated_safety_stock := GREATEST(
                ROUND(p_usage_std_dev * 2), 
                ROUND(p_avg_daily_usage * 0.5)
            );
            calculated_reorder_point := ROUND((p_avg_daily_usage * product_rec.manual_lead_time_days) + calculated_safety_stock);
            
            RETURN QUERY SELECT 
                calculated_reorder_point::INTEGER,
                calculated_safety_stock::INTEGER,
                product_rec.manual_lead_time_days::INTEGER,
                'automatic'::TEXT;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- ==================================================
-- MIGRATION COMPLETE
-- ==================================================

-- Verify migration
SELECT 
    'Migration completed successfully' as status,
    COUNT(*) as products_updated
FROM products 
WHERE forecasting_mode IS NOT NULL;
