import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from typing import List, Dict, Any

from backend.utils.database import (
    get_connection_pool, get_db_connection, get_db_cursor,
    execute_query, execute_batch_queries, execute_transaction,
    test_connection, is_connection_healthy, check_connection_pool_health,
    get_connection_health_status, reset_connection_pool, get_connection_info,
    wait_for_connection, get_database_size, get_table_sizes, get_database_statistics,
    optimize_connection_pool
)

from backend.exceptions import DatabaseError, ConnectionError


class TestConnectionPool:
    """Test connection pool functionality."""
    
    def test_get_connection_pool_success(self):
        """Test successful connection pool creation."""
        with patch('psycopg2.pool.SimpleConnectionPool') as mock_pool:
            mock_pool.return_value = Mock()
            
            pool = get_connection_pool()
            
            assert pool is not None
            mock_pool.assert_called_once()
    
    def test_get_connection_pool_failure(self):
        """Test connection pool creation failure."""
        with patch('psycopg2.pool.SimpleConnectionPool') as mock_pool:
            mock_pool.side_effect = Exception("Pool creation failed")
            
            with pytest.raises(DatabaseError):
                get_connection_pool()
    
    def test_reset_connection_pool(self):
        """Test connection pool reset."""
        with patch('backend.utils.database._connection_pool') as mock_pool:
            mock_pool.close = Mock()
            
            reset_connection_pool()
            
            mock_pool.close.assert_called_once()


class TestDatabaseConnection:
    """Test database connection functionality."""
    
    def test_get_db_connection_success(self):
        """Test successful database connection."""
        mock_pool = Mock()
        mock_connection = Mock()
        mock_pool.getconn.return_value = mock_connection
        
        with patch('backend.utils.database._connection_pool', mock_pool):
            with patch('backend.utils.database.is_connection_healthy', return_value=True):
                conn = get_db_connection()
                
                assert conn == mock_connection
                mock_pool.getconn.assert_called_once()
    
    def test_get_db_connection_unhealthy_retry(self):
        """Test connection retry when unhealthy."""
        mock_pool = Mock()
        mock_connection1 = Mock()
        mock_connection2 = Mock()
        mock_pool.getconn.side_effect = [mock_connection1, mock_connection2]
        
        with patch('backend.utils.database._connection_pool', mock_pool):
            with patch('backend.utils.database.is_connection_healthy') as mock_health:
                mock_health.side_effect = [False, True]  # First unhealthy, second healthy
                
                conn = get_db_connection()
                
                assert conn == mock_connection2
                assert mock_pool.getconn.call_count == 2
    
    def test_get_db_connection_max_retries_exceeded(self):
        """Test connection failure when max retries exceeded."""
        mock_pool = Mock()
        mock_connection = Mock()
        mock_pool.getconn.return_value = mock_connection
        
        with patch('backend.utils.database._connection_pool', mock_pool):
            with patch('backend.utils.database.is_connection_healthy', return_value=False):
                with pytest.raises(ConnectionError):
                    get_db_connection()
    
    def test_get_db_connection_pool_failure(self):
        """Test connection failure when pool is None."""
        with patch('backend.utils.database._connection_pool', None):
            with pytest.raises(DatabaseError):
                get_db_connection()


class TestDatabaseCursor:
    """Test database cursor functionality."""
    
    def test_get_db_cursor_success(self):
        """Test successful cursor creation."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        with patch('backend.utils.database.get_db_connection', return_value=mock_connection):
            with get_db_cursor() as cursor:
                assert cursor == mock_cursor
                mock_connection.cursor.assert_called_once()
            
            # Verify cleanup
            mock_cursor.close.assert_called_once()
            mock_connection.close.assert_called_once()
    
    def test_get_db_cursor_execution_error(self):
        """Test cursor error handling."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("SQL execution failed")
        mock_connection.cursor.return_value = mock_cursor
        
        with patch('backend.utils.database.get_db_connection', return_value=mock_connection):
            with pytest.raises(Exception):
                with get_db_cursor():
                    mock_cursor.execute("SELECT * FROM test")
            
            # Verify rollback and cleanup
            mock_connection.rollback.assert_called_once()
            mock_cursor.close.assert_called_once()
            mock_connection.close.assert_called_once()
    
    def test_get_db_cursor_connection_error(self):
        """Test cursor creation when connection fails."""
        with patch('backend.utils.database.get_db_connection') as mock_get_conn:
            mock_get_conn.side_effect = ConnectionError("Connection failed")
            
            with pytest.raises(ConnectionError):
                with get_db_cursor():
                    pass


class TestQueryExecution:
    """Test query execution functionality."""
    
    def test_execute_query_success(self):
        """Test successful query execution."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [{'id': 1, 'name': 'test'}]
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            result = execute_query("SELECT * FROM test")
            
            assert result == [{'id': 1, 'name': 'test'}]
            mock_cursor.execute.assert_called_once_with("SELECT * FROM test")
    
    def test_execute_query_error(self):
        """Test query execution error handling."""
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("SQL error")
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            with pytest.raises(DatabaseError):
                execute_query("SELECT * FROM test")
    
    def test_execute_batch_queries_success(self):
        """Test successful batch query execution."""
        queries = [
            ("INSERT INTO test (id, name) VALUES (%s, %s)", (1, 'test1')),
            ("INSERT INTO test (id, name) VALUES (%s, %s)", (2, 'test2'))
        ]
        
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = [[{'id': 1}], [{'id': 2}]]
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            results = execute_batch_queries(queries)
            
            assert len(results) == 2
            assert results[0] == [{'id': 1}]
            assert results[1] == [{'id': 2}]
            assert mock_cursor.execute.call_count == 2
    
    def test_execute_batch_queries_error(self):
        """Test batch query execution error handling."""
        queries = [
            ("INSERT INTO test (id, name) VALUES (%s, %s)", (1, 'test1')),
            ("INSERT INTO test (id, name) VALUES (%s, %s)", (2, 'test2'))
        ]
        
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = [True, Exception("SQL error")]
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            with pytest.raises(DatabaseError):
                execute_batch_queries(queries)
    
    def test_execute_transaction_success(self):
        """Test successful transaction execution."""
        def operation1():
            return True
        
        def operation2():
            return True
        
        operations = [operation1, operation2]
        
        mock_cursor = Mock()
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            result = execute_transaction(operations)
            
            assert result is True
            mock_cursor.execute.assert_called()  # Should execute operations
    
    def test_execute_transaction_error(self):
        """Test transaction execution error handling."""
        def operation1():
            return True
        
        def operation2():
            raise Exception("Operation failed")
        
        operations = [operation1, operation2]
        
        mock_cursor = Mock()
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            result = execute_transaction(operations)
            
            assert result is False
            # Should rollback on error
            mock_cursor.connection.rollback.assert_called_once()


class TestConnectionHealth:
    """Test connection health monitoring."""
    
    def test_is_connection_healthy_active(self):
        """Test healthy connection detection."""
        mock_connection = Mock()
        mock_connection.closed = 0
        
        result = is_connection_healthy(mock_connection)
        
        assert result is True
    
    def test_is_connection_healthy_closed(self):
        """Test unhealthy connection detection."""
        mock_connection = Mock()
        mock_connection.closed = 1
        
        result = is_connection_healthy(mock_connection)
        
        assert result is False
    
    def test_check_connection_pool_health(self):
        """Test connection pool health check."""
        mock_pool = Mock()
        mock_pool.minconn = 5
        mock_pool.maxconn = 20
        mock_pool.size = 10
        
        with patch('backend.utils.database._connection_pool', mock_pool):
            with patch('backend.utils.database._connection_health', {'is_healthy': True, 'last_check': time.time()}):
                health = check_connection_pool_health()
                
                assert 'pool_stats' in health
                assert 'health_status' in health
                assert health['pool_stats']['current_connections'] == 10
                assert health['pool_stats']['min_connections'] == 5
                assert health['pool_stats']['max_connections'] == 20
    
    def test_get_connection_health_status(self):
        """Test connection health status retrieval."""
        with patch('backend.utils.database._connection_health', {'is_healthy': True, 'last_check': time.time()}):
            status = get_connection_health_status()
            
            assert 'is_healthy' in status
            assert 'last_check' in status
            assert status['is_healthy'] is True
    
    def test_get_connection_health_status_with_check(self):
        """Test connection health status with health check."""
        with patch('backend.utils.database._connection_health', {'is_healthy': None}):
            with patch('backend.utils.database.test_connection', return_value=True):
                status = get_connection_health_status()
                
                assert status['is_healthy'] is True


class TestConnectionTesting:
    """Test connection testing functionality."""
    
    def test_test_connection_success(self):
        """Test successful connection test."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            result = test_connection()
            
            assert result is True
    
    def test_test_connection_failure(self):
        """Test connection test failure."""
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.side_effect = Exception("Connection failed")
            
            result = test_connection()
            
            assert result is False


class TestConnectionWaiting:
    """Test connection waiting functionality."""
    
    def test_wait_for_connection_success(self):
        """Test successful connection wait."""
        with patch('backend.utils.database.test_connection') as mock_test:
            mock_test.side_effect = [False, False, True]  # Fail twice, then succeed
            
            result = wait_for_connection(timeout=5, retry_interval=0.1)
            
            assert result is True
            assert mock_test.call_count == 3
    
    def test_wait_for_connection_timeout(self):
        """Test connection wait timeout."""
        with patch('backend.utils.database.test_connection', return_value=False):
            result = wait_for_connection(timeout=1, retry_interval=0.5)
            
            assert result is False


class TestDatabaseInformation:
    """Test database information retrieval."""
    
    def test_get_database_size(self):
        """Test database size retrieval."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1024]  # 1KB in bytes
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            size = get_database_size()
            
            assert size == "1.0 KB"
    
    def test_get_table_sizes(self):
        """Test table sizes retrieval."""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ['products', 1024],
            ['warehouses', 2048]
        ]
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            sizes = get_table_sizes()
            
            assert len(sizes) == 2
            assert sizes[0]['table_name'] == 'products'
            assert sizes[0]['size'] == '1.0 KB'
            assert sizes[1]['table_name'] == 'warehouses'
            assert sizes[1]['size'] == '2.0 KB'
    
    def test_get_database_statistics(self):
        """Test database statistics retrieval."""
        with patch('backend.utils.database.get_database_size', return_value="1.0 MB"):
            with patch('backend.utils.database.get_table_sizes', return_value=[{'table': 'test', 'size': '1.0 KB'}]):
                with patch('backend.utils.database.check_connection_pool_health', return_value={'status': 'healthy'}):
                    stats = get_database_statistics()
                    
                    assert 'database_size' in stats
                    assert 'table_sizes' in stats
                    assert 'connection_pool' in stats
                    assert stats['database_size'] == "1.0 MB"
                    assert len(stats['table_sizes']) == 1


class TestConnectionPoolOptimization:
    """Test connection pool optimization."""
    
    def test_optimize_connection_pool(self):
        """Test connection pool optimization recommendations."""
        mock_pool = Mock()
        mock_pool.minconn = 5
        mock_pool.maxconn = 20
        mock_pool.size = 10
        
        with patch('backend.utils.database._connection_pool', mock_pool):
            with patch('backend.utils.database.get_connection_info', return_value={'pool_stats': {'current_connections': 8}}):
                recommendations = optimize_connection_pool()
                
                assert 'current_usage' in recommendations
                assert 'recommendations' in recommendations
                assert recommendations['current_usage']['min_connections'] == 5
                assert recommendations['current_usage']['max_connections'] == 20
                assert recommendations['current_usage']['current_connections'] == 8


class TestConnectionInfo:
    """Test connection information retrieval."""
    
    def test_get_connection_info(self):
        """Test connection information retrieval."""
        with patch('backend.utils.database.check_connection_pool_health', return_value={'status': 'healthy'}):
            with patch('backend.utils.database.get_database_size', return_value="1.0 MB"):
                info = get_connection_info()
                
                assert 'health_status' in info
                assert 'pool_stats' in info
                assert 'database_size' in info
                assert info['health_status']['status'] == 'healthy'
                assert info['database_size'] == "1.0 MB"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_connection_pool_none(self):
        """Test handling when connection pool is None."""
        with patch('backend.utils.database._connection_pool', None):
            with pytest.raises(DatabaseError):
                get_db_connection()
    
    def test_connection_getconn_failure(self):
        """Test handling when pool.getconn() fails."""
        mock_pool = Mock()
        mock_pool.getconn.side_effect = Exception("getconn failed")
        
        with patch('backend.utils.database._connection_pool', mock_pool):
            with pytest.raises(ConnectionError):
                get_db_connection()
    
    def test_cursor_execute_failure(self):
        """Test handling when cursor.execute() fails."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("execute failed")
        mock_connection.cursor.return_value = mock_cursor
        
        with patch('backend.utils.database.get_db_connection', return_value=mock_connection):
            with pytest.raises(Exception):
                with get_db_cursor():
                    mock_cursor.execute("SELECT * FROM test")
            
            # Should rollback on error
            mock_connection.rollback.assert_called_once()


class TestPerformance:
    """Test performance characteristics."""
    
    def test_connection_pooling_efficiency(self):
        """Test that connection pooling is efficient."""
        mock_pool = Mock()
        mock_connection = Mock()
        mock_pool.getconn.return_value = mock_connection
        
        with patch('backend.utils.database._connection_pool', mock_pool):
            with patch('backend.utils.database.is_connection_healthy', return_value=True):
                # Get multiple connections
                conn1 = get_db_connection()
                conn2 = get_db_connection()
                
                # Should reuse pool efficiently
                assert mock_pool.getconn.call_count == 2
    
    def test_batch_query_efficiency(self):
        """Test that batch queries are efficient."""
        queries = [("SELECT * FROM test WHERE id = %s", (i,)) for i in range(100)]
        
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [{'id': i}]
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            start_time = time.time()
            results = execute_batch_queries(queries)
            end_time = time.time()
            
            # Should complete 100 queries efficiently
            assert len(results) == 100
            assert (end_time - start_time) < 1.0  # Should complete in under 1 second
    
    def test_transaction_efficiency(self):
        """Test that transactions are efficient."""
        def operation():
            return True
        
        operations = [operation for _ in range(50)]
        
        mock_cursor = Mock()
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            start_time = time.time()
            result = execute_transaction(operations)
            end_time = time.time()
            
            assert result is True
            assert (end_time - start_time) < 1.0  # Should complete in under 1 second


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_batch_queries(self):
        """Test batch queries with empty list."""
        result = execute_batch_queries([])
        
        assert result == []
    
    def test_empty_transaction_operations(self):
        """Test transaction with empty operations list."""
        result = execute_transaction([])
        
        assert result is True
    
    def test_very_large_queries(self):
        """Test handling of very large queries."""
        large_query = "SELECT * FROM " + "x" * 10000  # Very long query
        
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        
        with patch('backend.utils.database.get_db_cursor') as mock_get_cursor:
            mock_get_cursor.return_value.__enter__.return_value = mock_cursor
            
            # Should handle large queries without issues
            result = execute_query(large_query)
            
            assert result == []
    
    def test_connection_health_edge_cases(self):
        """Test connection health edge cases."""
        # Test with None connection
        result = is_connection_healthy(None)
        assert result is False
        
        # Test with connection without closed attribute
        mock_connection = Mock()
        del mock_connection.closed
        
        with pytest.raises(AttributeError):
            is_connection_healthy(mock_connection)
