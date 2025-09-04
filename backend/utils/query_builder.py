"""
Query Builder Utility for Inventory Management System
Provides a fluent interface for building complex SQL queries dynamically
"""

from typing import List, Dict, Any, Optional, Union
from enum import Enum


class JoinType(Enum):
    """Types of SQL joins"""
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL JOIN"


class OrderDirection(Enum):
    """SQL ORDER BY directions"""
    ASC = "ASC"
    DESC = "DESC"


class QueryBuilder:
    """Fluent SQL query builder"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.select_fields = ["*"]
        self.joins = []
        self.where_conditions = []
        self.where_params = []
        self.group_by_fields = []
        self.having_conditions = []
        self.having_params = []
        self.order_by_fields = []
        self.limit_value = None
        self.offset_value = None
        self.distinct = False
    
    def select(self, *fields: str) -> 'QueryBuilder':
        """Set SELECT fields"""
        if fields:
            self.select_fields = list(fields)
        return self
    
    def distinct_select(self, *fields: str) -> 'QueryBuilder':
        """Set DISTINCT SELECT fields"""
        self.distinct = True
        return self.select(*fields)
    
    def join(self, table: str, condition: str, join_type: JoinType = JoinType.INNER) -> 'QueryBuilder':
        """Add a JOIN clause"""
        self.joins.append({
            'type': join_type,
            'table': table,
            'condition': condition
        })
        return self
    
    def left_join(self, table: str, condition: str) -> 'QueryBuilder':
        """Add a LEFT JOIN clause"""
        return self.join(table, condition, JoinType.LEFT)
    
    def right_join(self, table: str, condition: str) -> 'QueryBuilder':
        """Add a RIGHT JOIN clause"""
        return self.join(table, condition, JoinType.RIGHT)
    
    def inner_join(self, table: str, condition: str) -> 'QueryBuilder':
        """Add an INNER JOIN clause"""
        return self.join(table, condition, JoinType.INNER)
    
    def where(self, condition: str, *params) -> 'QueryBuilder':
        """Add a WHERE condition"""
        self.where_conditions.append(condition)
        self.where_params.extend(params)
        return self
    
    def where_in(self, field: str, values: List[Any]) -> 'QueryBuilder':
        """Add WHERE IN condition"""
        if values:
            placeholders = ', '.join(['%s'] * len(values))
            condition = f"{field} IN ({placeholders})"
            self.where_conditions.append(condition)
            self.where_params.extend(values)
        return self
    
    def where_like(self, field: str, pattern: str) -> 'QueryBuilder':
        """Add WHERE LIKE condition"""
        return self.where(f"{field} LIKE %s", pattern)
    
    def where_ilike(self, field: str, pattern: str) -> 'QueryBuilder':
        """Add WHERE ILIKE condition (case-insensitive)"""
        return self.where(f"{field} ILIKE %s", pattern)
    
    def where_between(self, field: str, start_value: Any, end_value: Any) -> 'QueryBuilder':
        """Add WHERE BETWEEN condition"""
        return self.where(f"{field} BETWEEN %s AND %s", start_value, end_value)
    
    def where_null(self, field: str) -> 'QueryBuilder':
        """Add WHERE IS NULL condition"""
        return self.where(f"{field} IS NULL")
    
    def where_not_null(self, field: str) -> 'QueryBuilder':
        """Add WHERE IS NOT NULL condition"""
        return self.where(f"{field} IS NOT NULL")
    
    def where_date_range(self, field: str, start_date: str, end_date: str) -> 'QueryBuilder':
        """Add date range condition"""
        return self.where_between(field, start_date, end_date)
    
    def where_recent_days(self, field: str, days: int) -> 'QueryBuilder':
        """Add condition for recent days"""
        return self.where(f"{field} >= CURRENT_DATE - INTERVAL '%s days'", days)
    
    def group_by(self, *fields: str) -> 'QueryBuilder':
        """Add GROUP BY fields"""
        self.group_by_fields.extend(fields)
        return self
    
    def having(self, condition: str, *params) -> 'QueryBuilder':
        """Add HAVING condition"""
        self.having_conditions.append(condition)
        self.having_params.extend(params)
        return self
    
    def order_by(self, field: str, direction: OrderDirection = OrderDirection.ASC) -> 'QueryBuilder':
        """Add ORDER BY field"""
        self.order_by_fields.append(f"{field} {direction.value}")
        return self
    
    def limit(self, value: int) -> 'QueryBuilder':
        """Set LIMIT"""
        self.limit_value = value
        return self
    
    def offset(self, value: int) -> 'QueryBuilder':
        """Set OFFSET"""
        self.offset_value = value
        return self
    
    def build(self) -> tuple[str, tuple]:
        """Build the final SQL query and parameters"""
        # Build SELECT clause
        select_clause = "SELECT "
        if self.distinct:
            select_clause += "DISTINCT "
        select_clause += ", ".join(self.select_fields)
        
        # Build FROM clause
        from_clause = f" FROM {self.table_name}"
        
        # Build JOIN clauses
        join_clause = ""
        for join in self.joins:
            join_clause += f" {join['type'].value} {join['table']} ON {join['condition']}"
        
        # Build WHERE clause
        where_clause = ""
        if self.where_conditions:
            where_clause = " WHERE " + " AND ".join(self.where_conditions)
        
        # Build GROUP BY clause
        group_by_clause = ""
        if self.group_by_fields:
            group_by_clause = " GROUP BY " + ", ".join(self.group_by_fields)
        
        # Build HAVING clause
        having_clause = ""
        if self.having_conditions:
            having_clause = " HAVING " + " AND ".join(self.having_conditions)
        
        # Build ORDER BY clause
        order_by_clause = ""
        if self.order_by_fields:
            order_by_clause = " ORDER BY " + ", ".join(self.order_by_fields)
        
        # Build LIMIT clause
        limit_clause = ""
        if self.limit_value is not None:
            limit_clause = f" LIMIT {self.limit_value}"
        
        # Build OFFSET clause
        offset_clause = ""
        if self.offset_value is not None:
            offset_clause = f" OFFSET {self.offset_value}"
        
        # Combine all clauses
        query = (select_clause + from_clause + join_clause + where_clause + 
                group_by_clause + having_clause + order_by_clause + limit_clause + offset_clause)
        
        # Combine parameters
        params = tuple(self.where_params + self.having_params)
        
        return query, params
    
    def build_count_query(self) -> tuple[str, tuple]:
        """Build a COUNT query for pagination"""
        # Save original select fields
        original_select = self.select_fields.copy()
        
        # Build count query
        self.select_fields = ["COUNT(*) as total_count"]
        query, params = self.build()
        
        # Restore original select fields
        self.select_fields = original_select
        
        return query, params
    
    def build_paginated_query(self, page: int, per_page: int) -> tuple[str, tuple]:
        """Build a paginated query"""
        offset = (page - 1) * per_page
        return self.limit(per_page).offset(offset).build()
    
    def clone(self) -> 'QueryBuilder':
        """Create a copy of this query builder"""
        clone = QueryBuilder(self.table_name)
        clone.select_fields = self.select_fields.copy()
        clone.joins = self.joins.copy()
        clone.where_conditions = self.where_conditions.copy()
        clone.where_params = self.where_params.copy()
        clone.group_by_fields = self.group_by_fields.copy()
        clone.having_conditions = self.having_conditions.copy()
        clone.having_params = self.having_params.copy()
        clone.order_by_fields = self.order_by_fields.copy()
        clone.limit_value = self.limit_value
        clone.offset_value = self.offset_value
        clone.distinct = self.distinct
        return clone


class AdvancedQueryBuilder(QueryBuilder):
    """Advanced query builder with additional features"""
    
    def __init__(self, table_name: str):
        super().__init__(table_name)
        self.union_queries = []
        self.cte_queries = []
    
    def with_cte(self, name: str, query: str, params: tuple = ()) -> 'AdvancedQueryBuilder':
        """Add a Common Table Expression (CTE)"""
        self.cte_queries.append({
            'name': name,
            'query': query,
            'params': params
        })
        return self
    
    def union(self, query: str, params: tuple = ()) -> 'AdvancedQueryBuilder':
        """Add a UNION query"""
        self.union_queries.append({
            'query': query,
            'params': params
        })
        return self
    
    def build_with_cte(self) -> tuple[str, tuple]:
        """Build query with CTEs"""
        if not self.cte_queries:
            return self.build()
        
        # Build CTE clause
        cte_clause = "WITH "
        cte_definitions = []
        all_params = []
        
        for cte in self.cte_queries:
            cte_definitions.append(f"{cte['name']} AS ({cte['query']})")
            all_params.extend(cte['params'])
        
        cte_clause += ", ".join(cte_definitions)
        
        # Build main query
        main_query, main_params = self.build()
        all_params.extend(main_params)
        
        # Combine CTE and main query
        full_query = cte_clause + " " + main_query
        
        return full_query, tuple(all_params)
    
    def build_union_query(self) -> tuple[str, tuple]:
        """Build UNION query"""
        if not self.union_queries:
            return self.build()
        
        # Build main query
        main_query, main_params = self.build()
        all_params = list(main_params)
        
        # Add UNION queries
        union_clause = main_query
        for union in self.union_queries:
            union_clause += f" UNION {union['query']}"
            all_params.extend(union['params'])
        
        return union_clause, tuple(all_params)
    
    def build_full_query(self) -> tuple[str, tuple]:
        """Build full query with CTEs and UNIONs"""
        if self.cte_queries:
            return self.build_with_cte()
        elif self.union_queries:
            return self.build_union_query()
        else:
            return self.build()


# Utility functions for common query patterns
def build_search_query(table_name: str, search_fields: List[str], search_term: str) -> QueryBuilder:
    """Build a search query with multiple fields"""
    builder = QueryBuilder(table_name)
    
    if search_term:
        search_conditions = []
        for field in search_fields:
            search_conditions.append(f"{field} ILIKE %s")
        
        # Join conditions with OR
        where_clause = " OR ".join(search_conditions)
        builder.where(f"({where_clause})", *([f"%{search_term}%"] * len(search_fields)))
    
    return builder


def build_date_range_query(table_name: str, date_field: str, start_date: str, end_date: str) -> QueryBuilder:
    """Build a date range query"""
    builder = QueryBuilder(table_name)
    
    if start_date and end_date:
        builder.where_between(date_field, start_date, end_date)
    elif start_date:
        builder.where(f"{date_field} >= %s", start_date)
    elif end_date:
        builder.where(f"{date_field} <= %s", end_date)
    
    return builder


def build_paginated_query(table_name: str, page: int, per_page: int, order_by: str = None) -> QueryBuilder:
    """Build a paginated query"""
    builder = QueryBuilder(table_name)
    
    if order_by:
        builder.order_by(order_by)
    
    return builder.limit(per_page).offset((page - 1) * per_page)


def build_aggregation_query(table_name: str, group_by_fields: List[str], aggregate_fields: List[str]) -> QueryBuilder:
    """Build an aggregation query"""
    builder = QueryBuilder(table_name)
    
    # Set select fields to include group by and aggregate fields
    select_fields = group_by_fields + aggregate_fields
    builder.select(*select_fields)
    
    # Add group by
    builder.group_by(*group_by_fields)
    
    return builder
