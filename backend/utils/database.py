"""
Database utilities for Inventory Management System
Handles database connections, connection pooling, and error handling
"""

import psycopg2
import psycopg2.extras
import psycopg2.pool
from typing import Optional, Dict, Any
from contextlib import contextmanager
import logging

from config import get_config

# Configure logging
logger = logging.getLogger(__name__)

# Global connection pool
_connection_pool = None


def get_connection_pool():
    """Get or create database connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        config = get_config()
        db_config = config.get_db_config()
        
        try:
            _connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                **db_config
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    return _connection_pool


def get_db_connection():
    """Get database connection from pool"""
    try:
        pool = get_connection_pool()
        connection = pool.getconn()
        if connection is None:
            raise Exception("Failed to get connection from pool")
        return connection
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        raise


def return_db_connection(connection):
    """Return database connection to pool"""
    try:
        pool = get_connection_pool()
        pool.putconn(connection)
    except Exception as e:
        logger.error(f"Failed to return connection to pool: {e}")


@contextmanager
def get_db_cursor(cursor_factory=None):
    """Context manager for database cursor with automatic cleanup"""
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if cursor_factory:
            cursor = connection.cursor(cursor_factory=cursor_factory)
        else:
            cursor = connection.cursor()
        yield cursor
        connection.commit()
    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            return_db_connection(connection)


def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
    """Execute a database query with automatic connection management"""
    with get_db_cursor(psycopg2.extras.RealDictCursor) as cursor:
        cursor.execute(query, params)
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            return cursor.rowcount


def test_connection() -> bool:
    """Test database connection"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def close_connection_pool():
    """Close the database connection pool"""
    global _connection_pool
    
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Database connection pool closed")
