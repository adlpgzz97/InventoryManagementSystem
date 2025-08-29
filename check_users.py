#!/usr/bin/env python3
"""
Script to check what users exist in the database
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

def check_users():
    """Check what users exist in the database"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Check if users table exists
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                """)
                
                if not cursor.fetchone():
                    logger.info("Users table does not exist")
                    return
                
                # First check the table structure
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    ORDER BY ordinal_position
                """)
                
                columns = cursor.fetchall()
                logger.info("Users table structure:")
                for col in columns:
                    logger.info(f"  {col['column_name']}: {col['data_type']}")
                
                # List all users
                cursor.execute("""
                    SELECT * FROM users 
                    ORDER BY username
                """)
                
                results = cursor.fetchall()
                
                if results:
                    logger.info(f"Found {len(results)} users:")
                    for user in results:
                        logger.info(f"  Username: {user['username']}, Email: {user['email']}, Role: {user['role']}")
                else:
                    logger.info("No users found in the database")
                    
    except Exception as e:
        logger.error(f"Error checking users: {e}")

def check_auth_service():
    """Check if there's an auth service that creates default users"""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Check if there are any other user-related tables
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE '%user%'
                """)
                
                results = cursor.fetchall()
                logger.info("User-related tables:")
                for table in results:
                    logger.info(f"  {table['table_name']}")
                    
    except Exception as e:
        logger.error(f"Error checking auth service: {e}")

if __name__ == "__main__":
    check_users()
    check_auth_service()
