# Location Hierarchy System Guide

## Overview

The inventory management system now uses a flexible hierarchical location structure for organizing warehouse storage. This replaces the old simple aisle/bin system with a more sophisticated approach that allows for better organization and scalability.

## Location Structure

### Hierarchy Levels
The new system uses a 4-level hierarchy:

1. **Warehouse** - The main storage facility
2. **Area** - Storage areas within the warehouse (e.g., A01, A02, A03)
3. **Rack** - Storage racks within each area (e.g., R01, R02, R03)
4. **Level** - Storage levels within each rack (e.g., L1, L2, L3)

### Location Code Format
Locations are identified using a standardized code format:
```
W1-A01-R01-L1
```
Where:
- `W1` = Warehouse code
- `A01` = Area code
- `R01` = Rack code  
- `L1` = Level code

## Data Structure

### Database Tables

#### Warehouses Table
```sql
- id (UUID, Primary Key)
- name (Text)
- address (Text)
- code (VARCHAR) - Warehouse identifier (W1, W2, etc.)
```

#### Locations Table
```sql
- id (UUID, Primary Key)
- warehouse_id (UUID, Foreign Key)
- full_code (VARCHAR) - Complete location code (W1-A01-R01-L1)
- warehouse_code (VARCHAR) - Warehouse code component
- area_code (VARCHAR) - Area code component
- rack_code (VARCHAR) - Rack code component
- level_number (INTEGER) - Level number component
- bin_number (VARCHAR) - Bin number component (deprecated)
```

#### Bins Table
```sql
- id (UUID, Primary Key)
- code (VARCHAR) - Bin identifier (B01, B02, etc.)
- location_id (UUID, Foreign Key) - Links to locations table
```

#### Stock Items Table
```sql
- id (UUID, Primary Key)
- product_id (UUID, Foreign Key)
- bin_id (UUID, Foreign Key) - Links to bins table
- on_hand (INTEGER) - Quantity in stock
- qty_reserved (INTEGER) - Reserved quantity
```

## Warehouse Management

### Adding New Warehouses

When creating a new warehouse, you can customize the location structure using two methods:

#### 1. Quick Setup
Use the Quick Setup section to automatically generate a standard structure:
- **Number of Areas**: How many storage areas to create (1-10)
- **Racks per Area**: How many racks in each area (1-20)
- **Levels per Rack**: How many levels in each rack (1-10)

Example: 2 areas × 3 racks × 4 levels = 24 total locations

#### 2. Manual Customization
Build the structure manually by:
- Adding individual areas
- Adding racks to each area
- Adding levels to each rack
- Customizing names and codes for each level

### Editing Existing Warehouses

When editing a warehouse, the system provides:

#### Structure Visualization
- Hierarchical display of areas, racks, and levels
- Bin count for each level
- Occupation status (occupied vs. available bins)
- Visual indicators for occupied locations

#### Protection Mechanisms
The system prevents deletion of locations that contain stock:

1. **Level Protection**: Cannot delete levels with occupied bins
2. **Rack Protection**: Cannot delete racks with levels containing occupied bins
3. **Area Protection**: Cannot delete areas with racks containing occupied bins

#### Validation Features
- Confirmation dialogs when attempting to delete occupied locations
- Detailed error messages showing which locations are occupied
- Stock count information for occupied locations

## Location Customization

### Naming Conventions
You can customize names and codes at each level:

#### Areas
- **Default**: Area 01, Area 02, etc.
- **Custom**: Receiving Area, Shipping Area, Cold Storage, etc.
- **Codes**: A01, A02, A03, etc.

#### Racks
- **Default**: Rack 01, Rack 02, etc.
- **Custom**: Pallet Rack A, Mezzanine Rack, etc.
- **Codes**: R01, R02, R03, etc.

#### Levels
- **Default**: Level 1, Level 2, etc.
- **Custom**: Ground Level, Upper Level, etc.
- **Codes**: L1, L2, L3, etc.

### Code Formatting
- **Areas**: A + 2-digit number (A01, A02, A10)
- **Racks**: R + 2-digit number (R01, R02, R10)
- **Levels**: L + number (L1, L2, L10)

## Stock Management Integration

### Bin Assignment
- Bins are created independently and assigned to locations
- Multiple bins can be assigned to a single location
- Stock items are stored in bins, not directly in locations

### Location Tracking
- Stock items are tracked by their bin location
- Location hierarchy provides organizational structure
- Full location codes enable precise stock location tracking

### Occupation Detection
The system tracks:
- Total bins per location
- Occupied bins (bins with stock)
- Available bins (empty bins)

## Best Practices

### Structure Design
1. **Plan Ahead**: Design your hierarchy before creating warehouses
2. **Logical Grouping**: Group related items in the same area
3. **Scalability**: Leave room for expansion in each area
4. **Consistency**: Use consistent naming conventions

### Code Management
1. **Unique Codes**: Ensure codes are unique within each warehouse
2. **Meaningful Names**: Use descriptive names for better organization
3. **Standard Format**: Follow the established code format

### Stock Management
1. **Regular Audits**: Periodically verify stock locations
2. **Movement Tracking**: Use the system's transaction tracking
3. **Space Optimization**: Monitor bin utilization

## Migration from Old System

### Legacy Data
- Old aisle/bin data has been migrated to the new structure
- Existing stock items maintain their location assignments
- Historical data is preserved

### Compatibility
- The new system is backward compatible
- Existing APIs continue to work
- Data integrity is maintained during migration

## Troubleshooting

### Common Issues

#### Location Deletion Errors
**Problem**: Cannot delete a location
**Solution**: Check if the location has occupied bins. Move or remove stock items first.

#### Code Conflicts
**Problem**: Duplicate location codes
**Solution**: Ensure unique codes within each warehouse. Use different area/rack/level combinations.

#### Performance Issues
**Problem**: Slow warehouse loading
**Solution**: The system uses optimized queries with proper indexing for hierarchical data.

### Error Messages
- **"Cannot remove occupied locations"**: Location contains stock items
- **"Invalid location code"**: Code format doesn't match expected pattern
- **"Duplicate location code"**: Code already exists in the warehouse

## API Integration

### Location Queries
```sql
-- Get warehouse hierarchy
SELECT * FROM locations WHERE warehouse_id = ? ORDER BY full_code;

-- Get occupied locations
SELECT l.*, COUNT(si.id) as stock_count
FROM locations l
JOIN bins b ON l.id = b.location_id
JOIN stock_items si ON b.id = si.bin_id
WHERE l.warehouse_id = ? AND si.on_hand > 0
GROUP BY l.id;
```

### Hierarchical Data Format
```json
{
  "A01": {
    "name": "Receiving Area",
    "code": "A01",
    "racks": {
      "R01": {
        "name": "Pallet Rack A",
        "code": "R01",
        "levels": {
          "L1": {
            "name": "Ground Level",
            "code": "L1",
            "location_id": "uuid",
            "full_code": "W1-A01-R01-L1",
            "bin_count": 5,
            "occupied_bins": 2
          }
        }
      }
    }
  }
}
```

## Future Enhancements

### Planned Features
1. **Bulk Operations**: Add/remove multiple locations at once
2. **Template System**: Save and reuse warehouse layouts
3. **Advanced Analytics**: Location utilization reports
4. **Mobile Support**: Location management on mobile devices
5. **Integration**: Connect with warehouse management systems

### Scalability
The hierarchical system is designed to scale with:
- Multiple warehouses
- Complex storage layouts
- High-volume operations
- Real-time inventory tracking
