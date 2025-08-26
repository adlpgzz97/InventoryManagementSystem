#!/usr/bin/env python3
"""
Sample Data Population Script
Populates the PostgreSQL database with realistic sample data for testing
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

def populate_sample_data():
    """Execute the sample data SQL script"""
    try:
        print("* Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Read the sample data SQL file
        sample_data_file = Path(__file__).parent / 'db' / 'sample_data.sql'
        
        if not sample_data_file.exists():
            print("Error: sample_data.sql file not found!")
            return False
        
        print("* Reading sample data script...")
        with open(sample_data_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("* Executing sample data population...")
        print("  This may take a few moments...")
        
        # Execute the SQL script
        cur.execute(sql_script)
        
        # Get the summary results
        results = cur.fetchall()
        if results:
            print("\n* Population Summary:")
            for row in results:
                print(f"  Status: {row[0]}")
                print(f"  Warehouses: {row[1]}")
                print(f"  Locations: {row[2]}")
                print(f"  Products: {row[3]}")
                print(f"  Stock Items: {row[4]}")
                print(f"  Transactions: {row[5]}")
        
        # Commit the changes
        conn.commit()
        print("\n* Sample data populated successfully!")
        print("* The database now contains realistic inventory data for testing.")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error populating sample data: {e}")
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("INVENTORY SAMPLE DATA POPULATION")
    print("=" * 50)
    print()
    
    # Test database connection first
    try:
        print("* Testing database connection...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print("* Database connection successful!")
    except Exception as e:
        print(f"* Database connection failed: {e}")
        print("* Please ensure PostgreSQL is running and credentials are correct.")
        return
    
    # Confirm with user
    print()
    print("WARNING: This will replace existing sample data in the database.")
    response = input("Do you want to continue? (y/N): ").lower().strip()
    
    if response in ['y', 'yes']:
        print()
        success = populate_sample_data()
        
        if success:
            print()
            print("* You can now test the desktop application with realistic data!")
            print("* Run: python desktop/main.py")
        else:
            print("* Sample data population failed.")
    else:
        print("* Operation cancelled.")

if __name__ == '__main__':
    main()
