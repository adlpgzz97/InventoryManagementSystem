# Database Schema Analysis

## Overview
This document analyzes the database schema issues that are preventing stock items from displaying correctly in the application.

## Current Issues Identified

### 1. Stock Items Not Displaying
**Problem**: The stock page shows "No stock items found" despite the database containing 11 stock items.

**Root Causes**:
1. **Database Schema Mismatch**: Code expects columns that don't exist in the database
2. **Object Type Mismatch**: Code tries to access object methods on raw database rows

### 2. Database Schema Issues

#### Bins Table Schema
**Actual Schema**:
```sql
CREATE TABLE bins (
    id uuid PRIMARY KEY,
    code varchar(255),
    location_id uuid,
    created_at timestamp,
    updated_at timestamp
);
```

**Problem**: The code is trying to access a `name` column that doesn't exist in the bins table.

**Error**: `column "name" does not exist`

#### Stock Items Query Issues
**Current Query** (from `StockItem.get_all_with_locations()`):
```sql
SELECT 
    si.id, si.product_id, si.bin_id, si.on_hand, si.qty_reserved,
    si.batch_id, si.expiry_date, si.created_at,
    p.name as product_name, p.sku as product_sku,
    b.code as bin_code,
    l.full_code as location_code,
    w.name as warehouse_name
FROM stock_items si
JOIN products p ON si.product_id = p.id
JOIN bins b ON si.bin_id = b.id
LEFT JOIN locations l ON b.location_id = l.id
LEFT JOIN warehouses w ON l.warehouse_id = w.id
ORDER BY p.name, b.code
```

**Status**: This query works correctly and returns 11 results.

### 3. Code Issues

#### Object Type Mismatch
**Problem**: The stock route tries to access `available_stock` attribute on raw database rows.

**Error**: `'psycopg2.extras.RealDictRow object' has no attribute 'available_stock'`

**Location**: `backend/routes/stock.py` line 57
```python
stock_items = [item for item in stock_items if item['available_stock'] <= 5]
```

**Issue**: `item` is a `RealDictRow` (raw database result), not a `StockItem` object, so it doesn't have the `available_stock` property.

## Database Content Verification

### Stock Items
- **Count**: 11 items
- **Sample Item**: 
  ```python
  {
      'id': '1c67ec04-23ff-4a15-b9bf-f3c19ee5cec2',
      'product_id': '91e344cb-5889-409c-b0c6-22caab0e755d',
      'bin_id': 'f9951da5-71de-4fc6-ac29-809b1e73c932',
      'on_hand': 108,
      'qty_reserved': 0,
      'batch_id': None,
      'expiry_date': None,
      'created_at': datetime.datetime(2025, 8, 26, 9, 36, 8, 52970),
      'product_name': 'All-Purpose Cleaner',
      'product_sku': 'CLEAN-001',
      'bin_code': 'B1002',
      'location_code': 'A1F4',
      'warehouse_name': 'Wageningen Laboratory'
  }
  ```

### Related Tables
- **Products**: Contains product information (name, SKU)
- **Bins**: Contains bin codes and location references
- **Locations**: Contains location codes
- **Warehouses**: Contains warehouse names

## Solutions Required

### 1. Fix Stock Route Logic
**Problem**: The route tries to access `available_stock` on raw database rows.

**Solution**: Calculate `available_stock` from the raw data:
```python
# Instead of: item['available_stock']
# Use: item['on_hand'] - item['qty_reserved']
```

### 2. Fix Warehouse Model Queries
**Problem**: Code tries to access non-existent `name` column in bins table.

**Solution**: Update queries to use correct column names or add missing columns.

### 3. Standardize Data Handling
**Problem**: Mixing raw database rows with object methods.

**Solution**: Either:
- Convert all raw rows to proper objects, OR
- Use raw data consistently throughout

## Recommended Fixes

### Immediate Fix (Stock Route)
Update `backend/routes/stock.py` to handle raw database rows correctly:

```python
# For low stock filter
stock_items = [item for item in stock_items 
               if (item['on_hand'] - item['qty_reserved']) <= 5]

# For expired filter  
from datetime import datetime
stock_items = [item for item in stock_items 
               if item['expiry_date'] and 
               datetime.now().date() > item['expiry_date']]
```

### Long-term Fix (Schema Alignment)
1. **Update Database Schema**: Add missing columns to bins table if needed
2. **Standardize Data Access**: Use consistent approach for database results
3. **Add Validation**: Ensure all queries match actual schema

## Testing Results

### Database Query Test
- ✅ **Stock Items Query**: Returns 11 results correctly
- ✅ **Database Connection**: Working properly
- ✅ **Related Tables**: All joins working correctly

### Application Test
- ❌ **Stock Page Display**: Shows "No stock items found"
- ❌ **Route Processing**: Exception in stock route
- ❌ **Data Handling**: Object type mismatch

## Next Steps

1. **Fix Stock Route**: Update filtering logic to work with raw database rows
2. **Test Stock Page**: Verify stock items display correctly
3. **Fix Warehouse Model**: Resolve bins table column issues
4. **Add Error Handling**: Better error messages for schema mismatches
5. **Update Tests**: Ensure all tests work with actual schema

## Schema Documentation

### Tables Involved
- `stock_items`: Main inventory data
- `products`: Product information
- `bins`: Storage location bins
- `locations`: Physical locations
- `warehouses`: Warehouse information

### Key Relationships
- `stock_items.product_id` → `products.id`
- `stock_items.bin_id` → `bins.id`
- `bins.location_id` → `locations.id`
- `locations.warehouse_id` → `warehouses.id`

This analysis shows that the database contains the correct data, but the application code has schema mismatches and object type issues that prevent proper display.
