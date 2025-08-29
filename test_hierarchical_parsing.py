#!/usr/bin/env python3

def test_hierarchical_parsing():
    """Test the hierarchical parsing for different warehouse codes"""
    
    # Test location codes for different warehouses
    test_codes = [
        # Wageningen Laboratory (A)
        'A1A1', 'A1B1', 'A1C1', 'A2A1', 'A2B1',
        # Helmond Warehouse (B)  
        'B1A1', 'B1B1', 'B1C1', 'B1D1', 'B1E1',
        # Van 1 (C)
        'C1A1', 'C1B1', 'C1C1', 'C1D1', 'C1E1'
    ]
    
    print("Testing hierarchical parsing for different warehouse codes:")
    print("=" * 60)
    
    for code in test_codes:
        # Simulate the parsing logic
        if len(code) >= 4:
            warehouse_code = code[0]
            area_number = code[1] if len(code) > 1 and code[1].isdigit() else '1'
            area_code = f"A{area_number}"
            rack_letter = code[2] if len(code) > 2 else 'A'
            rack_code = f"R{ord(rack_letter) - ord('A') + 1:02d}"
            level_number = code[3:] if len(code) > 3 else '1'
            level_code = f"L{level_number}"
            
            print(f"Code: {code}")
            print(f"  Warehouse: {warehouse_code}")
            print(f"  Area: {area_code} (Area {area_number})")
            print(f"  Rack: {rack_code} (Rack {rack_letter})")
            print(f"  Level: {level_code} (Level {level_number})")
            print()

if __name__ == '__main__':
    test_hierarchical_parsing()
