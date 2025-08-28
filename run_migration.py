#!/usr/bin/env python3
"""
Database Migration Runner
Runs the new schema migration script
"""

import os
import psycopg2
import sys

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'inventory_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'TatUtil97==')
}

def run_migration():
    """Run the database migration"""
    print("🚀 Starting Database Migration...")
    print(f"📊 Connecting to database: {DB_CONFIG['database']} on {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False  # We'll handle transactions manually
        cur = conn.cursor()
        
        print("✅ Database connection established")
        
        # Read migration script
        with open('db/migration_new_schema.sql', 'r') as f:
            migration_sql = f.read()
        
        print("📝 Migration script loaded")
        
        # Execute migration
        print("🔄 Executing migration...")
        cur.execute(migration_sql)
        
        # Commit the transaction
        conn.commit()
        
        print("✅ Migration completed successfully!")
        
        # Verify the migration
        print("🔍 Verifying migration...")
        
        # Check if new tables exist
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('replenishment_policies', 'suppliers', 'product_suppliers')
            ORDER BY table_name
        """)
        
        new_tables = [row[0] for row in cur.fetchall()]
        print(f"📋 New tables created: {', '.join(new_tables)}")
        
        # Check if forecasting columns were removed from products
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'products' 
            AND column_name IN ('forecasting_mode', 'manual_reorder_point', 'manual_safety_stock', 'manual_lead_time_days', 'forecasting_notes')
        """)
        
        remaining_columns = [row[0] for row in cur.fetchall()]
        if remaining_columns:
            print(f"⚠️  Warning: Some forecasting columns still exist: {', '.join(remaining_columns)}")
        else:
            print("✅ Forecasting columns successfully removed from products table")
        
        # Check replenishment policies data
        cur.execute("SELECT COUNT(*) FROM replenishment_policies")
        policy_count = cur.fetchone()[0]
        print(f"📊 Replenishment policies created: {policy_count}")
        
        # Check indexes
        cur.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename IN ('replenishment_policies', 'product_suppliers')
            AND indexname LIKE 'idx_%'
        """)
        
        indexes = [row[0] for row in cur.fetchall()]
        print(f"🔗 Indexes created: {', '.join(indexes)}")
        
        cur.close()
        conn.close()
        
        print("\n🎉 Migration verification completed!")
        print("📋 Summary:")
        print(f"   - New tables: {len(new_tables)}")
        print(f"   - Replenishment policies: {policy_count}")
        print(f"   - Indexes: {len(indexes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
