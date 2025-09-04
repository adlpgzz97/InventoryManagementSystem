import pytest
from datetime import datetime, date
from typing import List, Dict, Any

from backend.utils.query_builder import (
    QueryBuilder, AdvancedQueryBuilder, JoinType, OrderDirection,
    build_search_query, build_date_range_query, build_paginated_query,
    build_aggregation_query
)


class TestQueryBuilder:
    """Test the basic QueryBuilder functionality."""
    
    def test_select_basic(self):
        """Test basic SELECT query building."""
        query = QueryBuilder().select('*').from_table('products').build()
        
        expected = "SELECT * FROM products"
        assert query.strip() == expected
    
    def test_select_specific_columns(self):
        """Test SELECT with specific columns."""
        query = QueryBuilder().select('id, name, price').from_table('products').build()
        
        expected = "SELECT id, name, price FROM products"
        assert query.strip() == expected
    
    def test_select_distinct(self):
        """Test DISTINCT SELECT."""
        query = QueryBuilder().distinct_select('category').from_table('products').build()
        
        expected = "SELECT DISTINCT category FROM products"
        assert query.strip() == expected
    
    def test_from_table(self):
        """Test FROM clause."""
        query = QueryBuilder().select('*').from_table('warehouses').build()
        
        expected = "SELECT * FROM warehouses"
        assert query.strip() == expected
    
    def test_where_simple(self):
        """Test simple WHERE clause."""
        query = QueryBuilder().select('*').from_table('products').where('price > 100').build()
        
        expected = "SELECT * FROM products WHERE price > 100"
        assert query.strip() == expected
    
    def test_where_multiple_conditions(self):
        """Test multiple WHERE conditions."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('price > 100')
                .where('category = %s')
                .build())
        
        expected = "SELECT * FROM products WHERE price > 100 AND category = %s"
        assert query.strip() == expected
    
    def test_where_in(self):
        """Test WHERE IN clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('category IN (%s, %s, %s)')
                .build())
        
        expected = "SELECT * FROM products WHERE category IN (%s, %s, %s)"
        assert query.strip() == expected
    
    def test_where_like(self):
        """Test WHERE LIKE clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('name LIKE %s')
                .build())
        
        expected = "SELECT * FROM products WHERE name LIKE %s"
        assert query.strip() == expected
    
    def test_where_ilike(self):
        """Test WHERE ILIKE clause (case insensitive)."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('name ILIKE %s')
                .build())
        
        expected = "SELECT * FROM products WHERE name ILIKE %s"
        assert query.strip() == expected
    
    def test_where_between(self):
        """Test WHERE BETWEEN clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('price BETWEEN %s AND %s')
                .build())
        
        expected = "SELECT * FROM products WHERE price BETWEEN %s AND %s"
        assert query.strip() == expected
    
    def test_where_null(self):
        """Test WHERE IS NULL clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('description IS NULL')
                .build())
        
        expected = "SELECT * FROM products WHERE description IS NULL"
        assert query.strip() == expected
    
    def test_where_not_null(self):
        """Test WHERE IS NOT NULL clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('description IS NOT NULL')
                .build())
        
        expected = "SELECT * FROM products WHERE description IS NOT NULL"
        assert query.strip() == expected
    
    def test_where_date_range(self):
        """Test WHERE date range clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('created_at >= %s')
                .where('created_at <= %s')
                .build())
        
        expected = "SELECT * FROM products WHERE created_at >= %s AND created_at <= %s"
        assert query.strip() == expected
    
    def test_where_recent_days(self):
        """Test WHERE recent days clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('created_at >= CURRENT_DATE - INTERVAL %s DAYS')
                .build())
        
        expected = "SELECT * FROM products WHERE created_at >= CURRENT_DATE - INTERVAL %s DAYS"
        assert query.strip() == expected
    
    def test_join_inner(self):
        """Test INNER JOIN."""
        query = (QueryBuilder()
                .select('p.name, s.quantity')
                .from_table('products p')
                .join('stock_items s', 'p.id = s.product_id', JoinType.INNER)
                .build())
        
        expected = "SELECT p.name, s.quantity FROM products p INNER JOIN stock_items s ON p.id = s.product_id"
        assert query.strip() == expected
    
    def test_join_left(self):
        """Test LEFT JOIN."""
        query = (QueryBuilder()
                .select('p.name, s.quantity')
                .from_table('products p')
                .join('stock_items s', 'p.id = s.product_id', JoinType.LEFT)
                .build())
        
        expected = "SELECT p.name, s.quantity FROM products p LEFT JOIN stock_items s ON p.id = s.product_id"
        assert query.strip() == expected
    
    def test_join_right(self):
        """Test RIGHT JOIN."""
        query = (QueryBuilder()
                .select('p.name, s.quantity')
                .from_table('products p')
                .join('stock_items s', 'p.id = s.product_id', JoinType.RIGHT)
                .build())
        
        expected = "SELECT p.name, s.quantity FROM products p RIGHT JOIN stock_items s ON p.id = s.product_id"
        assert query.strip() == expected
    
    def test_group_by(self):
        """Test GROUP BY clause."""
        query = (QueryBuilder()
                .select('category, COUNT(*) as count')
                .from_table('products')
                .group_by('category')
                .build())
        
        expected = "SELECT category, COUNT(*) as count FROM products GROUP BY category"
        assert query.strip() == expected
    
    def test_having(self):
        """Test HAVING clause."""
        query = (QueryBuilder()
                .select('category, COUNT(*) as count')
                .from_table('products')
                .group_by('category')
                .having('COUNT(*) > 5')
                .build())
        
        expected = "SELECT category, COUNT(*) as count FROM products GROUP BY category HAVING COUNT(*) > 5"
        assert query.strip() == expected
    
    def test_order_by_asc(self):
        """Test ORDER BY ASC."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .order_by('name', OrderDirection.ASC)
                .build())
        
        expected = "SELECT * FROM products ORDER BY name ASC"
        assert query.strip() == expected
    
    def test_order_by_desc(self):
        """Test ORDER BY DESC."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .order_by('price', OrderDirection.DESC)
                .build())
        
        expected = "SELECT * FROM products ORDER BY price DESC"
        assert query.strip() == expected
    
    def test_order_by_multiple(self):
        """Test multiple ORDER BY clauses."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .order_by('category', OrderDirection.ASC)
                .order_by('price', OrderDirection.DESC)
                .build())
        
        expected = "SELECT * FROM products ORDER BY category ASC, price DESC"
        assert query.strip() == expected
    
    def test_limit(self):
        """Test LIMIT clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .limit(10)
                .build())
        
        expected = "SELECT * FROM products LIMIT 10"
        assert query.strip() == expected
    
    def test_offset(self):
        """Test OFFSET clause."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .offset(20)
                .build())
        
        expected = "SELECT * FROM products OFFSET 20"
        assert query.strip() == expected
    
    def test_limit_and_offset(self):
        """Test LIMIT and OFFSET together."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .limit(10)
                .offset(20)
                .build())
        
        expected = "SELECT * FROM products LIMIT 10 OFFSET 20"
        assert query.strip() == expected
    
    def test_complex_query(self):
        """Test a complex query with multiple clauses."""
        query = (QueryBuilder()
                .select('p.name, p.category, COUNT(s.id) as stock_count')
                .from_table('products p')
                .join('stock_items s', 'p.id = s.product_id', JoinType.LEFT)
                .where('p.price > %s')
                .where('p.category IN (%s, %s)')
                .group_by('p.name, p.category')
                .having('COUNT(s.id) > 0')
                .order_by('stock_count', OrderDirection.DESC)
                .limit(20)
                .build())
        
        expected = ("SELECT p.name, p.category, COUNT(s.id) as stock_count "
                   "FROM products p "
                   "LEFT JOIN stock_items s ON p.id = s.product_id "
                   "WHERE p.price > %s AND p.category IN (%s, %s) "
                   "GROUP BY p.name, p.category "
                   "HAVING COUNT(s.id) > 0 "
                   "ORDER BY stock_count DESC "
                   "LIMIT 20")
        assert query.strip() == expected
    
    def test_build_count_query(self):
        """Test building count query."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .where('price > 100')
                .build_count_query())
        
        expected = "SELECT COUNT(*) FROM products WHERE price > 100"
        assert query.strip() == expected
    
    def test_build_paginated_query(self):
        """Test building paginated query."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .build_paginated_query(page=2, page_size=10))
        
        expected = "SELECT * FROM products LIMIT 10 OFFSET 10"
        assert query.strip() == expected
    
    def test_clone(self):
        """Test cloning a query builder."""
        original = (QueryBuilder()
                   .select('*')
                   .from_table('products')
                   .where('price > 100'))
        
        cloned = original.clone().where('category = %s')
        
        original_query = original.build()
        cloned_query = cloned.build()
        
        assert original_query != cloned_query
        assert 'category = %s' in cloned_query
        assert 'category = %s' not in original_query


class TestAdvancedQueryBuilder:
    """Test the AdvancedQueryBuilder functionality."""
    
    def test_with_cte(self):
        """Test Common Table Expression (CTE)."""
        query = (AdvancedQueryBuilder()
                .with_cte('product_stats', 
                          'SELECT category, COUNT(*) as count FROM products GROUP BY category')
                .select('*')
                .from_table('product_stats')
                .build_with_cte())
        
        expected = ("WITH product_stats AS (SELECT category, COUNT(*) as count FROM products GROUP BY category) "
                   "SELECT * FROM product_stats")
        assert query.strip() == expected
    
    def test_multiple_ctes(self):
        """Test multiple CTEs."""
        query = (AdvancedQueryBuilder()
                .with_cte('product_stats', 
                          'SELECT category, COUNT(*) as count FROM products GROUP BY category')
                .with_cte('warehouse_stats',
                          'SELECT warehouse_id, COUNT(*) as count FROM stock_items GROUP BY warehouse_id')
                .select('*')
                .from_table('product_stats')
                .build_with_cte())
        
        expected = ("WITH product_stats AS (SELECT category, COUNT(*) as count FROM products GROUP BY category), "
                   "warehouse_stats AS (SELECT warehouse_id, COUNT(*) as count FROM stock_items GROUP BY warehouse_id) "
                   "SELECT * FROM product_stats")
        assert query.strip() == expected
    
    def test_union(self):
        """Test UNION query."""
        query = (AdvancedQueryBuilder()
                .select('id, name, category')
                .from_table('products')
                .where('category = %s')
                .union()
                .select('id, name, category')
                .from_table('archived_products')
                .where('category = %s')
                .build_union_query())
        
        expected = ("SELECT id, name, category FROM products WHERE category = %s "
                   "UNION "
                   "SELECT id, name, category FROM archived_products WHERE category = %s")
        assert query.strip() == expected
    
    def test_union_all(self):
        """Test UNION ALL query."""
        query = (AdvancedQueryBuilder()
                .select('id, name, category')
                .from_table('products')
                .where('category = %s')
                .union(all_union=True)
                .select('id, name, category')
                .from_table('archived_products')
                .where('category = %s')
                .build_union_query())
        
        expected = ("SELECT id, name, category FROM products WHERE category = %s "
                   "UNION ALL "
                   "SELECT id, name, category FROM archived_products WHERE category = %s")
        assert query.strip() == expected
    
    def test_complex_advanced_query(self):
        """Test a complex advanced query with CTE and UNION."""
        query = (AdvancedQueryBuilder()
                .with_cte('active_products',
                          'SELECT * FROM products WHERE is_active = true')
                .with_cte('product_stock',
                          'SELECT p.id, p.name, COALESCE(SUM(s.quantity), 0) as total_stock '
                          'FROM active_products p '
                          'LEFT JOIN stock_items s ON p.id = s.product_id '
                          'GROUP BY p.id, p.name')
                .select('*')
                .from_table('product_stock')
                .where('total_stock > 0')
                .union()
                .select('id, name, 0 as total_stock')
                .from_table('archived_products')
                .where('archived_date > %s')
                .build_full_query())
        
        expected = ("WITH active_products AS (SELECT * FROM products WHERE is_active = true), "
                   "product_stock AS (SELECT p.id, p.name, COALESCE(SUM(s.quantity), 0) as total_stock "
                   "FROM active_products p "
                   "LEFT JOIN stock_items s ON p.id = s.product_id "
                   "GROUP BY p.id, p.name) "
                   "SELECT * FROM product_stock WHERE total_stock > 0 "
                   "UNION "
                   "SELECT id, name, 0 as total_stock FROM archived_products WHERE archived_date > %s")
        assert query.strip() == expected


class TestUtilityFunctions:
    """Test the utility functions for building common query patterns."""
    
    def test_build_search_query(self):
        """Test building search query."""
        query = build_search_query(
            table='products',
            search_term='laptop',
            search_columns=['name', 'description', 'category']
        )
        
        expected = ("SELECT * FROM products WHERE "
                   "name ILIKE %s OR description ILIKE %s OR category ILIKE %s")
        assert query.strip() == expected
    
    def test_build_date_range_query(self):
        """Test building date range query."""
        query = build_date_range_query(
            table='transactions',
            date_column='transaction_date',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        expected = ("SELECT * FROM transactions WHERE "
                   "transaction_date >= %s AND transaction_date <= %s")
        assert query.strip() == expected
    
    def test_build_paginated_query_utility(self):
        """Test building paginated query utility."""
        query = build_paginated_query(
            base_query="SELECT * FROM products",
            page=3,
            page_size=25
        )
        
        expected = "SELECT * FROM products LIMIT 25 OFFSET 50"
        assert query.strip() == expected
    
    def test_build_aggregation_query(self):
        """Test building aggregation query."""
        query = build_aggregation_query(
            table='stock_items',
            group_by_columns=['warehouse_id', 'product_id'],
            aggregate_columns=['quantity'],
            aggregate_functions=['SUM', 'COUNT']
        )
        
        expected = ("SELECT warehouse_id, product_id, "
                   "SUM(quantity) as sum_quantity, COUNT(quantity) as count_quantity "
                   "FROM stock_items GROUP BY warehouse_id, product_id")
        assert query.strip() == expected


class TestQueryBuilderEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_query(self):
        """Test building an empty query."""
        query = QueryBuilder().build()
        
        # Should return a minimal valid query
        assert query.strip() == "SELECT *"
    
    def test_no_from_table(self):
        """Test query without FROM clause."""
        query = QueryBuilder().select('*').build()
        
        assert query.strip() == "SELECT *"
    
    def test_where_without_conditions(self):
        """Test WHERE clause without conditions."""
        query = (QueryBuilder()
                .select('*')
                .from_table('products')
                .build())
        
        assert query.strip() == "SELECT * FROM products"
    
    def test_invalid_join_type(self):
        """Test invalid join type handling."""
        with pytest.raises(ValueError):
            QueryBuilder().join('table', 'condition', 'INVALID')
    
    def test_invalid_order_direction(self):
        """Test invalid order direction handling."""
        with pytest.raises(ValueError):
            QueryBuilder().order_by('column', 'INVALID')
    
    def test_negative_limit(self):
        """Test negative limit handling."""
        query = QueryBuilder().select('*').from_table('products').limit(-5).build()
        
        # Should handle negative values gracefully
        assert 'LIMIT -5' in query
    
    def test_negative_offset(self):
        """Test negative offset handling."""
        query = QueryBuilder().select('*').from_table('products').offset(-10).build()
        
        # Should handle negative values gracefully
        assert 'OFFSET -10' in query


class TestQueryBuilderPerformance:
    """Test query builder performance characteristics."""
    
    def test_large_query_performance(self):
        """Test performance with large number of conditions."""
        builder = QueryBuilder().select('*').from_table('products')
        
        # Add many WHERE conditions
        for i in range(100):
            builder.where(f'field{i} = %s')
        
        query = builder.build()
        
        # Should complete in reasonable time
        assert len(query) > 0
        assert query.count('AND') == 99  # 100 conditions = 99 ANDs
    
    def test_memory_usage(self):
        """Test memory usage with large queries."""
        builder = QueryBuilder().select('*').from_table('products')
        
        # Add many columns
        columns = [f'col{i}' for i in range(1000)]
        builder.select(', '.join(columns))
        
        query = builder.build()
        
        # Should handle large queries without excessive memory usage
        assert len(query) > 0
        assert query.count('col') == 1000
