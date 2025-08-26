#!/usr/bin/env python3
"""
Database migration script to add batch tracking features
"""

import psycopg2
import os

def run_migration():
    """Run the database migration"""
    
    # Database configuration
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432'),
        'database': os.environ.get('DB_NAME', 'inventory_db'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'TatUtil97==')
    }
    
    print("Running database migration...")
    print(f"Connecting to database: {DB_CONFIG['database']} on {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Read migration SQL file
        migration_file = 'db/migration_batch_tracking.sql'
        if not os.path.exists(migration_file):
            print(f"Error: Migration file {migration_file} not found")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("Executing migration...")
        
        # Execute the migration
        cur.execute(migration_sql)
        
        # Verify the migration
        print("Verifying migration...")
        
        # Check if batch_tracked column exists in products
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'products' AND column_name = 'batch_tracked'
        """)
        if cur.fetchone():
            print("✓ batch_tracked column added to products table")
        else:
            print("✗ batch_tracked column not found")
            return False
        
        # Check if stock_transactions table exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'stock_transactions'
        """)
        if cur.fetchone():
            print("✓ stock_transactions table created")
        else:
            print("✗ stock_transactions table not found")
            return False
        
        # Check if batch_id column exists in stock_items
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'stock_items' AND column_name = 'batch_id'
        """)
        if cur.fetchone():
            print("✓ batch_id column added to stock_items table")
        else:
            print("✗ batch_id column not found")
            return False
        
        # Check if expiry_date column exists in stock_items
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'stock_items' AND column_name = 'expiry_date'
        """)
        if cur.fetchone():
            print("✓ expiry_date column added to stock_items table")
        else:
            print("✗ expiry_date column not found")
            return False
        
        # Count sample data added
        cur.execute("SELECT COUNT(*) FROM products WHERE sku IN ('SKU004', 'SKU005')")
        sample_products = cur.fetchone()[0]
        print(f"✓ {sample_products} sample batch-tracked products added")
        
        cur.execute("SELECT COUNT(*) FROM stock_items WHERE batch_id IS NOT NULL")
        batch_items = cur.fetchone()[0]
        print(f"✓ {batch_items} batch-tracked stock items added")
        
        cur.close()
        conn.close()
        
        print("\n🎉 Migration completed successfully!")
        print("Database now supports batch tracking and audit trail features.")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if not success:
        exit(1)
