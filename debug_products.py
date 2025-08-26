#!/usr/bin/env python3
"""
Debug script to check products in database
"""

import psycopg2
import psycopg2.extras
import os

def check_products():
    """Check products in database"""
    
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
        
        # Check total count
        cur.execute("SELECT COUNT(*) as count FROM products")
        total_count = cur.fetchone()['count']
        print(f"Total products in database: {total_count}")
        
        # Get all products
        cur.execute("SELECT * FROM products ORDER BY created_at DESC")
        products_data = cur.fetchall()
        
        print(f"\nProducts found: {len(products_data)}")
        
        for i, product in enumerate(products_data):
            print(f"\nProduct {i+1}:")
            print(f"  ID: {product['id']}")
            print(f"  SKU: {product['sku']}")
            print(f"  Name: {product['name']}")
            print(f"  Description: {product['description']}")
            print(f"  Batch Tracked: {product.get('batch_tracked', 'N/A')}")
            print(f"  Created At: {product.get('created_at', 'N/A')}")
        
        # Check if there are any issues with the data
        if products_data:
            # Test the same query as the app
            cur.execute("SELECT * FROM products ORDER BY created_at DESC")
            test_data = cur.fetchall()
            products_list = [dict(row) for row in test_data] if test_data else []
            print(f"\nConverted to list of dicts: {len(products_list)} items")
            
            if products_list:
                print("First product as dict:")
                print(products_list[0])
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_products()
