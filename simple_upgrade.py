#!/usr/bin/env python3
"""
Simple Database Upgrade Script
Applies essential batch tracking migration and populates sample data
"""

import psycopg2
import os
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'inventory_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'TatUtil97==')
}

def run_sql_file(connection, file_path, description):
    """Execute SQL file and handle errors"""
    try:
        print(f"* Running {description}...")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        cursor = connection.cursor()
        cursor.execute(sql_content)
        connection.commit()
        cursor.close()
        
        print(f"  ✓ {description} completed successfully")
        return True
        
    except Exception as e:
        print(f"  ✗ Error in {description}: {e}")
        connection.rollback()
        return False

def main():
    """Main upgrade process"""
    print("=" * 60)
    print("INVENTORY DATABASE SIMPLE UPGRADE")
    print("Adding Batch Tracking and Sample Data")
    print("=" * 60)
    
    try:
        # Connect to database
        print("* Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        print("  ✓ Connected successfully")
        
        # Apply simple migration
        migration_file = Path(__file__).parent / 'db' / 'simple_migration.sql'
        if not run_sql_file(conn, migration_file, "Simple Batch Tracking Migration"):
            print("\n✗ Migration failed. Aborting upgrade.")
            return False
        
        # Populate sample data
        sample_data_file = Path(__file__).parent / 'db' / 'simple_sample_data.sql'
        if not run_sql_file(conn, sample_data_file, "Sample Data Population"):
            print("\n✗ Sample data population failed.")
            return False
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ DATABASE UPGRADE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("* Batch tracking features added")
        print("* Sample data populated")
        print("* Ready to test the application")
        print("\nNext steps:")
        print("1. Run the desktop application: python desktop/main.py")
        print("2. Login with: admin / admin123")
        print("3. Explore the enhanced features!")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Database connection failed: {e}")
        print("\nPlease ensure:")
        print("1. PostgreSQL is running")
        print("2. Database 'inventory_db' exists")
        print("3. Connection details are correct")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
