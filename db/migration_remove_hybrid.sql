-- Migration script to remove hybrid forecasting mode
-- This removes the 'hybrid' option from the forecasting_mode CHECK constraint

-- ==================================================
-- 1. UPDATE EXISTING HYBRID RECORDS TO AUTOMATIC
-- ==================================================

-- Convert any existing 'hybrid' records to 'automatic'
UPDATE products 
SET forecasting_mode = 'automatic' 
WHERE forecasting_mode = 'hybrid';

-- ==================================================
-- 2. UPDATE THE CHECK CONSTRAINT
-- ==================================================

-- Drop the existing constraint
ALTER TABLE products DROP CONSTRAINT IF EXISTS products_forecasting_mode_check;

-- Add the new constraint without 'hybrid'
ALTER TABLE products ADD CONSTRAINT products_forecasting_mode_check 
CHECK (forecasting_mode IN ('automatic', 'manual'));

-- ==================================================
-- 3. UPDATE THE FORECASTING FUNCTION
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
    'Hybrid mode removed successfully' as status,
    COUNT(*) as products_with_automatic_mode
FROM products 
WHERE forecasting_mode = 'automatic';

SELECT 
    'Manual mode count' as status,
    COUNT(*) as products_with_manual_mode
FROM products 
WHERE forecasting_mode = 'manual';
