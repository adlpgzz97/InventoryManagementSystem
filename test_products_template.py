#!/usr/bin/env python3
"""
Test script to verify products template rendering
"""

import psycopg2
import psycopg2.extras
import os
from flask import Flask, render_template
from pathlib import Path

# Create a minimal Flask app for testing
app = Flask(__name__, template_folder='backend/views')

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'inventory_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'TatUtil97==')
}

def get_products():
    """Get products from database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY created_at DESC")
        products_data = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to list of dicts
        products_list = [dict(row) for row in products_data] if products_data else []
        return products_list
    except Exception as e:
        print(f"Error getting products: {e}")
        return []

@app.route('/test')
def test_products():
    """Test products template"""
    products = get_products()
    print(f"Found {len(products)} products")
    
    # Test template rendering
    try:
        html = render_template('products.html', products=products)
        print("Template rendered successfully")
        
        # Check if the "No products found" message appears
        if "No products found" in html:
            print("ERROR: 'No products found' message appears in rendered HTML")
        else:
            print("SUCCESS: Products are being displayed correctly")
        
        return html
    except Exception as e:
        print(f"Template rendering error: {e}")
        return f"Error: {e}"

if __name__ == "__main__":
    print("Testing products template...")
    products = get_products()
    print(f"Database has {len(products)} products")
    
    if products:
        print(f"First product: {products[0]['name']}")
    
    # Test template rendering
    with app.app_context():
        try:
            html = render_template('products.html', products=products)
            print("Template rendered successfully")
            
            # Check if the "No products found" message appears
            if "No products found" in html:
                print("ERROR: 'No products found' message appears in rendered HTML")
            else:
                print("SUCCESS: Products are being displayed correctly")
        except Exception as e:
            print(f"Template rendering error: {e}")
            import traceback
            traceback.print_exc()
