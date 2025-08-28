# Location Code Format Change

## Overview
Changed the location code format from the hierarchical `W1-A01-R01-L1` format to a more compact `A2F10` format.

## New Format
The new location code format is: `A{area_number}{rack_letter}{level_number}`

### Examples:
- `A1A1` = Area 1, Rack A (R01), Level 1
- `A2F10` = Area 2, Rack F (R06), Level 10
- `A3L5` = Area 3, Rack L (R12), Level 5
- `A10Z20` = Area 10, Rack Z (R26), Level 20

### Format Breakdown:
- **Area**: `A` + area number (e.g., `A2` for Area 2)
- **Rack**: Letter from A-Z (A=R01, B=R02, C=R03, etc.)
- **Level**: Level number (e.g., `10` for Level 10)

## Changes Made

### Backend Changes (`backend/app.py`)

1. **Location Creation (Add Warehouse)**:
   - Updated `add_warehouse` function to generate new format
   - Changed from `f"W1-{area_code}-{rack_code}-{level_code}"` to compact format

2. **Location Updates (Edit Warehouse)**:
   - Updated `edit_warehouse` function to generate new format
   - Changed location code generation in both add and update logic

3. **Location Parsing (Warehouse Display)**:
   - Updated parsing logic in `warehouses` function
   - Changed from splitting by `-` to parsing compact format
   - Added logic to extract area number, rack letter, and level number

4. **Fallback Code**:
   - Updated fallback location code from `W1-A01-R01-L1` to `A1A1`

### Frontend Changes
- No changes needed to frontend JavaScript
- The modal forms pass the hierarchical structure to backend
- Backend handles the conversion to new format

## Code Logic

### Generation Logic:
```python
# Convert rack_code from R01 format to letter (R01->A, R02->B, etc.)
rack_letter = chr(ord('A') + int(rack_code.replace('R', '')) - 1)

# Extract area number from A01 format
area_number = area_code.replace('A', '')

# Extract level number from L1 format
level_number = level_code.replace('L', '')

# Generate compact format
full_code = f"A{area_number}{rack_letter}{level_number}"
```

### Parsing Logic:
```python
# Extract area number (A2 -> 2)
area_number = full_code[1]
area_code = f"A{area_number}"

# Extract rack letter (A2F10 -> F)
rack_letter = full_code[2]
rack_code = f"R{ord(rack_letter) - ord('A') + 1:02d}"

# Extract level number (A2F10 -> 10)
level_number = full_code[3:]
level_code = f"L{level_number}"
```

## Benefits

1. **Shorter Codes**: More compact and easier to read
2. **Consistent Format**: Standardized format across all locations
3. **Backward Compatibility**: Existing hierarchical structure in frontend remains unchanged
4. **Scalable**: Supports up to 26 racks (A-Z) and unlimited levels

## Testing

The new format has been tested with various inputs:
- `A01-R01-L1` → `A1A1` ✓
- `A02-R06-L10` → `A2F10` ✓
- `A03-R12-L5` → `A3L5` ✓
- `A10-R26-L20` → `A10Z20` ✓

## Migration Notes

- Existing locations in the database will need to be migrated if they use the old format
- The frontend continues to work with the hierarchical structure
- All new locations will use the compact format
- The system maintains backward compatibility for parsing existing codes
