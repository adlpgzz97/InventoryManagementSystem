"""
Database utilities for Inventory Management System
Handles database connections, connection pooling, and error handling
"""

import psycopg2
import psycopg2.extras
import psycopg2.pool
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import logging
import os
import time
from datetime import datetime, timedelta

from backend.config import config
from backend.exceptions import DatabaseError, ConnectionError

# Configure logging
logger = logging.getLogger(__name__)

# Global connection pool
_connection_pool = None
_connection_health = {
    'last_check': None,
    'is_healthy': True,
    'error_count': 0,
    'last_error': None
}


def get_connection_pool():
    """Get or create database connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        logger.info("Creating new database connection pool...")
        try:
            # Use centralized configuration
            db_config = config.DB_CONFIG
            
            # Add connection timeout settings to prevent freezing
            db_config_with_timeouts = {
                **db_config,
                'connect_timeout': 10,  # 10 seconds connection timeout
                'options': '-c statement_timeout=30000',  # 30 seconds query timeout
                'application_name': 'inventory_app'
            }
            
            _connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=5,      # Increased from 1
                maxconn=50,     # Increased from 20
                **db_config_with_timeouts
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise DatabaseError(f"Failed to create connection pool: {str(e)}")
    else:
        logger.debug("Using existing database connection pool")
    
    return _connection_pool


def get_db_connection():
    """Get database connection from pool"""
    try:
        pool = get_connection_pool()
        connection = pool.getconn()
        if connection is None:
            raise ConnectionError("Failed to get connection from pool")
        
        # Check connection health
        if not is_connection_healthy(connection):
            # Return connection to pool and get a new one
            pool.putconn(connection)
            connection = pool.getconn()
            if connection is None:
                raise ConnectionError("Failed to get healthy connection from pool")
        
        return connection
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        _update_connection_health(False, str(e))
        raise DatabaseError(f"Failed to get database connection: {str(e)}")


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
            try:
                connection.rollback()
            except:
                pass
        logger.error(f"Database operation failed: {e}")
        _update_connection_health(False, str(e))
        raise DatabaseError(f"Database operation failed: {str(e)}")
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if connection:
            return_db_connection(connection)


def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
    """Execute a database query with automatic connection management"""
    try:
        with get_db_cursor(psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return None
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise DatabaseError(f"Query execution failed: {str(e)}")


def execute_query_with_timeout(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False, timeout: int = 10):
    """Execute a database query with timeout to prevent freezing"""
    import threading
    
    result = None
    exception = None
    
    def execute_query_thread():
        nonlocal result, exception
        try:
            result = execute_query(query, params, fetch_one, fetch_all)
        except Exception as e:
            exception = e
    
    # Create and start thread
    thread = threading.Thread(target=execute_query_thread)
    thread.daemon = True
    thread.start()
    
    # Wait for completion or timeout
    thread.join(timeout)
    
    if thread.is_alive():
        logger.error(f"Database query timed out after {timeout} seconds: {query[:50]}...")
        raise DatabaseError(f"Database query timed out after {timeout} seconds")
    
    if exception:
        raise exception
    
    return result


def execute_batch_queries(queries: List[tuple]) -> List[Any]:
    """Execute multiple queries in a single transaction"""
    try:
        with get_db_cursor() as cursor:
            results = []
            for query, params in queries:
                cursor.execute(query, params)
                if cursor.description:  # Query returns results
                    results.append(cursor.fetchall())
                else:
                    results.append(cursor.rowcount)
            return results
    except Exception as e:
        logger.error(f"Batch query execution failed: {e}")
        raise DatabaseError(f"Batch query execution failed: {str(e)}")


def execute_transaction(operations: List[callable]) -> bool:
    """Execute multiple operations in a single transaction"""
    try:
        with get_db_cursor() as cursor:
            for operation in operations:
                if not operation(cursor):
                    raise DatabaseError(f"Operation failed: {operation.__name__}")
            return True
    except Exception as e:
        logger.error(f"Transaction execution failed: {e}")
        raise DatabaseError(f"Transaction execution failed: {str(e)}")


def test_connection():
    """Test database connectivity"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            _update_connection_health(True)
            logger.info("Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        _update_connection_health(False, str(e))
        return False


def is_connection_healthy(connection) -> bool:
    """Check if a specific connection is healthy"""
    try:
        if connection.closed:
            return False
        
        # Test with a simple query
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True
    except Exception:
        return False


def check_connection_pool_health() -> Dict[str, Any]:
    """Check the health of the connection pool"""
    try:
        pool = get_connection_pool()
        
        # Get pool stats
        pool_stats = {
            'minconn': pool.minconn,
            'maxconn': pool.maxconn,
            'current_connections': pool.size(),
            'available_connections': pool.size() - pool.size()
        }
        
        # Test a connection
        test_success = test_connection()
        
        return {
            'pool_stats': pool_stats,
            'connection_test': test_success,
            'overall_health': test_success and pool_stats['current_connections'] > 0,
            'last_check': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Connection pool health check failed: {e}")
        return {
            'pool_stats': {},
            'connection_test': False,
            'overall_health': False,
            'last_check': datetime.now().isoformat(),
            'error': str(e)
        }


def _update_connection_health(is_healthy: bool, error_message: str = None):
    """Update connection health status"""
    global _connection_health
    
    _connection_health['last_check'] = datetime.now()
    _connection_health['is_healthy'] = is_healthy
    
    if is_healthy:
        _connection_health['error_count'] = 0
        _connection_health['last_error'] = None
    else:
        _connection_health['error_count'] += 1
        _connection_health['last_error'] = error_message


def get_connection_health_status() -> Dict[str, Any]:
    """Get current connection health status"""
    global _connection_health
    
    # Perform health check if not done recently
    if (_connection_health['last_check'] is None or 
        datetime.now() - _connection_health['last_check'] > timedelta(minutes=5)):
        test_connection()
    
    return {
        'is_healthy': _connection_health['is_healthy'],
        'last_check': _connection_health['last_check'].isoformat() if _connection_health['last_check'] else None,
        'error_count': _connection_health['error_count'],
        'last_error': _connection_health['last_error'],
        'pool_health': check_connection_pool_health()
    }


def reset_connection_pool():
    """Reset the connection pool (useful for recovery)"""
    global _connection_pool, _connection_health
    
    try:
        if _connection_pool:
            _connection_pool.closeall()
            logger.info("Connection pool closed")
        
        _connection_pool = None
        _connection_health = {
            'last_check': None,
            'is_healthy': True,
            'error_count': 0,
            'last_error': None
        }
        
        logger.info("Connection pool reset completed")
        return True
    except Exception as e:
        logger.error(f"Failed to reset connection pool: {e}")
        return False


def get_connection_info():
    """Get database connection information (without sensitive data)"""
    db_config = config.DB_CONFIG
    health_status = get_connection_health_status()
    
    return {
        'host': db_config['host'],
        'port': db_config['port'],
        'database': db_config['database'],
        'user': db_config['user'],
        'connected': health_status['is_healthy'],
        'health_status': health_status,
        'pool_stats': health_status['pool_health']['pool_stats']
    }


def wait_for_connection(timeout: int = 30, retry_interval: float = 1.0) -> bool:
    """Wait for database connection to become available"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if test_connection():
            return True
        time.sleep(retry_interval)
    
    logger.error(f"Database connection timeout after {timeout} seconds")
    return False


def get_database_size() -> Optional[str]:
    """Get the size of the database"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """)
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Failed to get database size: {e}")
        return None


def get_table_sizes() -> List[Dict[str, Any]]:
    """Get sizes of all tables in the database"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY size_bytes DESC
            """)
            results = cursor.fetchall()
            
            return [
                {
                    'schema': row[0],
                    'table': row[1],
                    'size': row[2],
                    'size_bytes': row[3]
                }
                for row in results
            ]
    except Exception as e:
        logger.error(f"Failed to get table sizes: {e}")
        return []


def get_database_statistics() -> Dict[str, Any]:
    """Get comprehensive database statistics"""
    try:
        stats = {
            'connection_health': get_connection_health_status(),
            'database_size': get_database_size(),
            'table_sizes': get_table_sizes(),
            'connection_info': get_connection_info()
        }
        
        # Add performance metrics if available
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT version()")
                version_result = cursor.fetchone()
                stats['postgres_version'] = version_result[0] if version_result else 'Unknown'
        except:
            stats['postgres_version'] = 'Unknown'
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get database statistics: {e}")
        return {'error': str(e)}


def optimize_connection_pool():
    """Optimize connection pool based on usage patterns"""
    try:
        health_status = get_connection_health_status()
        pool_stats = health_status['pool_health']['pool_stats']
        
        # Adjust pool size based on usage
        current_connections = pool_stats['current_connections']
        max_connections = pool_stats['maxconn']
        
        if current_connections > max_connections * 0.8:
            # High usage - consider increasing pool size
            logger.info("High connection pool usage detected")
            return {
                'recommendation': 'increase_pool_size',
                'current_usage_percent': (current_connections / max_connections) * 100
            }
        elif current_connections < max_connections * 0.2:
            # Low usage - consider decreasing pool size
            logger.info("Low connection pool usage detected")
            return {
                'recommendation': 'decrease_pool_size',
                'current_usage_percent': (current_connections / max_connections) * 100
            }
        else:
            return {
                'recommendation': 'maintain_current_size',
                'current_usage_percent': (current_connections / max_connections) * 100
            }
    except Exception as e:
        logger.error(f"Failed to optimize connection pool: {e}")
        return {'error': str(e)}
