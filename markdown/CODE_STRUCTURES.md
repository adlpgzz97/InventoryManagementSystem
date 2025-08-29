# Code Structure Documentation

This document contains the actual code structures used in the inventory management system based on database analysis.

## Warehouse Codes
**Format**: Single letter codes
**Examples**: 
- `A` = Wageningen Laboratory
- `B` = Helmond Warehouse  
- `C` = Van 1

## Location Codes
**Format**: `[Warehouse][Section][Area][Sub-Area]` (4 characters)
**Structure**: `X1YZ` where:
- `X` = Warehouse code (A, B, C)
- `1` = Section (always 1 in current data)
- `Y` = Area (A, B, C, D, E, F, etc.)
- `Z` = Sub-area (1, 2, 3, 4, 5, 6, 7, 8)

**Examples**:
- `A1D8` = Wageningen Lab, Section 1, Area D, Sub-area 8
- `C1A6` = Van 1, Section 1, Area A, Sub-area 6
- `B1B1` = Helmond Warehouse, Section 1, Area B, Sub-area 1

## Bin Codes
**Format**: `B[4-digit number]`
**Examples**: `B1001`, `B1002`, `B1005`, `B1014`
**Pattern**: Always starts with "B" followed by a 4-digit sequential number

## Product SKUs
**Format**: Various patterns
**Examples**:
- `SKU004`, `SKU005` (Sequential SKU format)
- `OFFICE-002` (Category-Number format)
- `MED-001`, `MED-002` (Category-Number format)

## Complete Location Hierarchy
```
Warehouse Code (A/B/C) 
    ↓
Location Code (X1YZ) 
    ↓  
Bin Code (B####)
    ↓
Stock Items
```

**Example Chain**:
- Warehouse: `A` (Wageningen Laboratory)
- Location: `A1F4` (Section 1, Area F, Sub-area 4)
- Bin: `B1002`
- Product: All-Purpose Cleaner

## Database Relationships
- **stock_items.bin_id** → **bins.id**
- **bins.location_id** → **locations.id**
- **locations.warehouse_id** → **warehouses.id**

## Location Grid System
The location codes follow a **hierarchical grid system** where:
- First character = Warehouse
- Second character = Section (currently all "1")
- Third character = Area (A, B, C, D, E, F, etc.)
- Fourth character = Sub-area (1-8)

This gives a **logical grid layout** within each warehouse, making it easy to locate items physically.

## Sample Data from Database
```
=== WAREHOUSE CODES ===
Name: Wageningen Laboratory, Code: A
Name: Van 1, Code: C
Name: Helmond Warehouse, Code: B

=== LOCATION CODES ===
Location: A1D8, A1E1, A1E2, A1E3, A1E4, A1E5, A1E6, A1E7, A1E8, A1F1

=== BIN CODES ===
Bin: B1001, B1002, B1007, B1009, B1012, B1013, B1014, B1015, B1016, B1019

=== PRODUCT SKUS ===
Name: Batch Product A, SKU: SKU004
Name: Batch Product B, SKU: SKU005
Name: Ballpoint Pens, SKU: OFFICE-002
Name: Surgical Mask Pack, SKU: MED-001
Name: Latex Gloves, SKU: MED-002

=== STOCK ITEMS WITH LOCATIONS ===
Product: All-Purpose Cleaner, Bin: B1002, Location: A1F4, Warehouse: Wageningen Laboratory
Product: Laboratory Ethanol, Bin: B1001, Location: C1A6, Warehouse: Van 1
Product: Batch Product B, Bin: B1006, Location: C1B5, Warehouse: Van 1
Product: All-Purpose Cleaner, Bin: B1014, Location: C1C3, Warehouse: Van 1
Product: USB Cables, Bin: B1005, Location: B1B1, Warehouse: Helmond Warehouse
```

## Notes for Development
- Location codes are stored in the `full_code` field of the `locations` table
- Bin codes follow the pattern `B[0-9]+` with a database constraint
- The relationship chain must be properly joined for stock display
- Missing location relationships can cause stock loading issues
