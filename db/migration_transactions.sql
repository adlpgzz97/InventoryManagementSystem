-- Migration script to ensure stock_transactions table exists with correct structure
-- This migration ensures the transactions page has the required database structure

-- ==================================================
-- 1. CREATE STOCK_TRANSACTIONS TABLE IF NOT EXISTS
-- ==================================================

CREATE TABLE IF NOT EXISTS stock_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_item_id UUID NOT NULL REFERENCES stock_items(id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('receive', 'ship', 'adjust', 'transfer', 'reserve', 'release')),
    quantity_change INTEGER NOT NULL,
    quantity_before INTEGER NOT NULL,
    quantity_after INTEGER NOT NULL,
    reference_id UUID,
    notes TEXT,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ==================================================
-- 2. CREATE INDEXES FOR PERFORMANCE
-- ==================================================

CREATE INDEX IF NOT EXISTS idx_stock_transactions_stock_item_id ON stock_transactions(stock_item_id);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_created_at ON stock_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_type ON stock_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_stock_transactions_user_id ON stock_transactions(user_id);

-- ==================================================
-- 3. ADD SAMPLE TRANSACTION DATA (if table is empty)
-- ==================================================

-- Only add sample data if the table is empty
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM stock_transactions LIMIT 1) THEN
        -- Get some existing stock items to create sample transactions
        INSERT INTO stock_transactions (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id)
        SELECT 
            si.id,
            'receive',
            si.qty_available,
            0,
            si.qty_available,
            'Initial stock receipt',
            (SELECT id FROM users WHERE role = 'admin' LIMIT 1)
        FROM stock_items si
        WHERE si.qty_available > 0
        LIMIT 5;
        
        -- Add some sample adjustments
        INSERT INTO stock_transactions (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id)
        SELECT 
            si.id,
            'adjust',
            -5,
            si.qty_available,
            GREATEST(si.qty_available - 5, 0),
            'Stock adjustment - damaged items',
            (SELECT id FROM users WHERE role = 'manager' LIMIT 1)
        FROM stock_items si
        WHERE si.qty_available >= 10
        LIMIT 3;
        
        -- Add some sample shipments
        INSERT INTO stock_transactions (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id)
        SELECT 
            si.id,
            'ship',
            -10,
            si.qty_available,
            GREATEST(si.qty_available - 10, 0),
            'Customer order shipment',
            (SELECT id FROM users WHERE role = 'worker' LIMIT 1)
        FROM stock_items si
        WHERE si.qty_available >= 15
        LIMIT 2;
    END IF;
END $$;

-- ==================================================
-- 4. CREATE HELPER FUNCTIONS FOR TRANSACTIONS
-- ==================================================

-- Function to create a transaction and update stock levels
CREATE OR REPLACE FUNCTION create_stock_transaction(
    p_stock_item_id UUID,
    p_transaction_type TEXT,
    p_quantity_change INTEGER,
    p_notes TEXT DEFAULT NULL,
    p_reference_id UUID DEFAULT NULL,
    p_user_id UUID DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_transaction_id UUID;
    v_quantity_before INTEGER;
    v_quantity_after INTEGER;
BEGIN
    -- Get current stock level
    SELECT qty_available INTO v_quantity_before
    FROM stock_items
    WHERE id = p_stock_item_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Stock item not found';
    END IF;
    
    -- Calculate new quantity
    v_quantity_after := v_quantity_before + p_quantity_change;
    
    -- Validate stock levels for outgoing transactions
    IF p_transaction_type IN ('ship', 'transfer') AND v_quantity_after < 0 THEN
        RAISE EXCEPTION 'Insufficient stock for this transaction';
    END IF;
    
    -- Update stock levels
    UPDATE stock_items
    SET qty_available = v_quantity_after
    WHERE id = p_stock_item_id;
    
    -- Create transaction record
    INSERT INTO stock_transactions 
    (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id, reference_id)
    VALUES (p_stock_item_id, p_transaction_type, p_quantity_change, v_quantity_before, v_quantity_after, p_notes, p_user_id, p_reference_id)
    RETURNING id INTO v_transaction_id;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get transaction statistics
CREATE OR REPLACE FUNCTION get_transaction_stats(
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL
) RETURNS TABLE(
    total_transactions BIGINT,
    total_received BIGINT,
    total_shipped BIGINT,
    total_adjusted BIGINT,
    unique_products BIGINT,
    unique_stock_items BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_transactions,
        SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END)::BIGINT as total_received,
        SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END)::BIGINT as total_shipped,
        SUM(CASE WHEN st.transaction_type = 'adjust' THEN st.quantity_change ELSE 0 END)::BIGINT as total_adjusted,
        COUNT(DISTINCT p.id)::BIGINT as unique_products,
        COUNT(DISTINCT st.stock_item_id)::BIGINT as unique_stock_items
    FROM stock_transactions st
    LEFT JOIN stock_items si ON st.stock_item_id = si.id
    LEFT JOIN products p ON si.product_id = p.id
    WHERE (p_date_from IS NULL OR st.created_at >= p_date_from)
      AND (p_date_to IS NULL OR st.created_at <= p_date_to);
END;
$$ LANGUAGE plpgsql;

-- ==================================================
-- MIGRATION COMPLETE
-- ==================================================

-- Display summary
SELECT 
    'Stock Transactions Migration Complete' as status,
    COUNT(*) as total_transactions,
    COUNT(DISTINCT stock_item_id) as unique_stock_items
FROM stock_transactions;
