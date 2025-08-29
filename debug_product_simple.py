#!/usr/bin/env python3
"""
Simple debug script to check if a specific product exists in the database
"""

import psycopg2
import psycopg2.extras
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'inventory_db',
    'user': 'postgres',
    'password': 'TatUtil97=='
}

def check_product_exists(product_id):
    """Check if a product exists in the database"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, name, sku, description 
                    FROM products 
                    WHERE id = %s
                    """,
                    (product_id,)
                )
                
                result = cursor.fetchone()
                
                if result:
                    logger.info(f"Product found: {result}")
                    return True
                else:
                    logger.warning(f"No product found with ID: {product_id}")
                    return False
                    
    except Exception as e:
        logger.error(f"Error checking product: {e}")
        return False

def list_all_products():
    """List all products in the database"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, name, sku 
                    FROM products 
                    ORDER BY name
                    """
                )
                
                results = cursor.fetchall()
                
                logger.info(f"Found {len(results)} products:")
                for product in results:
                    logger.info(f"  ID: {product['id']}, Name: {product['name']}, SKU: {product['sku']}")
                    
                return results
                
    except Exception as e:
        logger.error(f"Error listing products: {e}")
        return []

def search_laboratory_ethanol():
    """Search for products with 'laboratory ethanol' in the name"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, name, sku 
                    FROM products 
                    WHERE name ILIKE %s
                    """,
                    ('%laboratory%ethanol%',)
                )
                
                results = cursor.fetchall()
                
                if results:
                    logger.info(f"Found {len(results)} products with 'laboratory ethanol' in name:")
                    for product in results:
                        logger.info(f"  ID: {product['id']}, Name: {product['name']}, SKU: {product['sku']}")
                else:
                    logger.info("No products found with 'laboratory ethanol' in name")
                    
                return results
                
    except Exception as e:
        logger.error(f"Error searching for laboratory ethanol: {e}")
        return []

if __name__ == "__main__":
    # The specific product ID that's causing the 404 error
    problematic_id = "7fbadf57-b5de-43b1-a174-6d6cb7c4cd51"
    
    logger.info("=== Debugging Product 404 Error ===")
    logger.info(f"Checking for product ID: {problematic_id}")
    
    # Check if the specific product exists
    exists = check_product_exists(problematic_id)
    
    if not exists:
        logger.info("\n=== Listing All Products ===")
        list_all_products()
        
        logger.info("\n=== Checking for 'laboratory ethanol' ===")
        search_laboratory_ethanol()
