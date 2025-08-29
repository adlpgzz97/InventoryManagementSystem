#!/usr/bin/env python3
"""
Debug script to check if a specific product exists in the database
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.utils.database import execute_query
from backend.config import get_config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_product_exists(product_id):
    """Check if a product exists in the database"""
    try:
        # Query the products table
        result = execute_query(
            """
            SELECT id, name, sku, description 
            FROM products 
            WHERE id = %s
            """,
            (product_id,),
            fetch_one=True
        )
        
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
        results = execute_query(
            """
            SELECT id, name, sku 
            FROM products 
            ORDER BY name
            """,
            fetch_all=True
        )
        
        logger.info(f"Found {len(results)} products:")
        for product in results:
            logger.info(f"  ID: {product['id']}, Name: {product['name']}, SKU: {product['sku']}")
            
        return results
        
    except Exception as e:
        logger.error(f"Error listing products: {e}")
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
        
        # Also check for products with similar names
        logger.info("\n=== Checking for 'laboratory ethanol' ===")
        try:
            results = execute_query(
                """
                SELECT id, name, sku 
                FROM products 
                WHERE name ILIKE %s
                """,
                ('%laboratory%ethanol%',),
                fetch_all=True
            )
            
            if results:
                logger.info(f"Found {len(results)} products with 'laboratory ethanol' in name:")
                for product in results:
                    logger.info(f"  ID: {product['id']}, Name: {product['name']}, SKU: {product['sku']}")
            else:
                logger.info("No products found with 'laboratory ethanol' in name")
                
        except Exception as e:
            logger.error(f"Error searching for laboratory ethanol: {e}")
