#!/usr/bin/env python3
"""
Migration script to add categories table and update products table
Run this script to add proper category support to the inventory system
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.database import execute_query
from backend.config import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the categories table migration"""
    try:
        logger.info("Starting categories table migration...")
        
        # Read the SQL migration file
        migration_file = Path(__file__).parent / "add_categories_table.sql"
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split the SQL into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            if statement:
                logger.info(f"Executing statement {i}/{len(statements)}")
                try:
                    execute_query(statement)
                    logger.info(f"✓ Statement {i} executed successfully")
                except Exception as e:
                    logger.error(f"✗ Error executing statement {i}: {e}")
                    logger.error(f"Statement: {statement[:100]}...")
                    raise
        
        logger.info("✅ Categories table migration completed successfully!")
        
        # Verify the migration
        verify_migration()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

def verify_migration():
    """Verify that the migration was successful"""
    try:
        logger.info("Verifying migration...")
        
        # Check if categories table exists and has data
        categories = execute_query("SELECT COUNT(*) as count FROM categories", fetch_all=True)
        if categories:
            logger.info(f"✓ Categories table created with {categories[0]['count']} categories")
        
        # Check if products table has category_id column
        products_with_categories = execute_query(
            "SELECT COUNT(*) as count FROM products WHERE category_id IS NOT NULL", 
            fetch_all=True
        )
        if products_with_categories:
            logger.info(f"✓ {products_with_categories[0]['count']} products now have categories assigned")
        
        # Show the categories that were created
        category_list = execute_query(
            "SELECT code, description FROM categories ORDER BY code", 
            fetch_all=True
        )
        logger.info("Categories created:")
        for cat in category_list:
            logger.info(f"  - {cat['code']}: {cat['description']}")
        
        logger.info("✅ Migration verification completed!")
        
    except Exception as e:
        logger.error(f"❌ Migration verification failed: {e}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("Categories Table Migration")
    print("=" * 60)
    print(f"Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    print()
    
    try:
        run_migration()
        print("\n🎉 Migration completed successfully!")
        print("You can now use proper categories in your products.")
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        sys.exit(1)
