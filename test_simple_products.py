#!/usr/bin/env python3
"""
Simple test to check products data
"""

import psycopg2
import psycopg2.extras
import os

def test_products_data():
    """Test products data directly"""
    
    # Database configuration
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432'),
        'database': os.environ.get('DB_NAME', 'inventory_db'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'TatUtil97==')
    }
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY created_at DESC")
        products_data = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to list of dicts (same as the app)
        products_list = [dict(row) for row in products_data] if products_data else []
        
        print(f"Products found: {len(products_list)}")
        print(f"Products is truthy: {bool(products_list)}")
        
        if products_list:
            print(f"First product: {products_list[0]['name']}")
            print(f"First product keys: {list(products_list[0].keys())}")
            
            # Check if batch_tracked exists
            if 'batch_tracked' in products_list[0]:
                print(f"batch_tracked value: {products_list[0]['batch_tracked']}")
            else:
                print("WARNING: batch_tracked field not found!")
        
        return products_list
        
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    products = test_products_data()
    
    # Test the exact condition from the template
    if products:
        print("\n✓ Template condition '{% if products %}' would be TRUE")
        print("✓ Products should be displayed")
    else:
        print("\n✗ Template condition '{% if products %}' would be FALSE")
        print("✗ 'No products found' message would be shown")
