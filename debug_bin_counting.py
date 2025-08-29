#!/usr/bin/env python3
"""
Debug script to investigate bin counting issues in the hierarchical view
"""

import psycopg2
import os
from collections import defaultdict

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'inventory_db',
    'user': 'postgres',
    'password': 'TatUtil97=='
}

def connect_db():
    """Connect to the database"""
    return psycopg2.connect(**DB_CONFIG)

def analyze_rack_bin_counts():
    """Analyze actual bin counts vs what the hierarchical view shows"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("=== BIN COUNTING ANALYSIS ===\n")
    
    # Get all warehouses
    cursor.execute("SELECT id, name, code FROM warehouses ORDER BY name")
    warehouses = cursor.fetchall()
    
    for warehouse_id, warehouse_name, warehouse_code in warehouses:
        print(f"Warehouse: {warehouse_name} (Code: {warehouse_code})")
        print("-" * 50)
        
        # Get all locations for this warehouse
        cursor.execute("""
            SELECT id, full_code 
            FROM locations 
            WHERE warehouse_id = %s 
            ORDER BY full_code
        """, (warehouse_id,))
        locations = cursor.fetchall()
        
        # Group locations by rack
        rack_data = defaultdict(lambda: {'locations': [], 'actual_bins': 0, 'empty_locations': 0})
        
        for location_id, full_code in locations:
            if len(full_code) >= 4:
                # Parse location code
                warehouse_code_char = full_code[0]
                area_number = full_code[1] if len(full_code) > 1 and full_code[1].isdigit() else '1'
                rack_letter = full_code[2] if len(full_code) > 2 else 'A'
                level_number = full_code[3:] if len(full_code) > 3 else '1'
                
                rack_key = f"A{area_number}{rack_letter}"
                
                # Count actual bins for this location
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM bins 
                    WHERE location_id = %s
                """, (location_id,))
                bin_count = cursor.fetchone()[0]
                
                rack_data[rack_key]['locations'].append({
                    'full_code': full_code,
                    'bin_count': bin_count
                })
                
                if bin_count > 0:
                    rack_data[rack_key]['actual_bins'] += bin_count
                else:
                    rack_data[rack_key]['empty_locations'] += 1
        
        # Display results for each rack
        for rack_key, data in sorted(rack_data.items()):
            total_locations = len(data['locations'])
            actual_bins = data['actual_bins']
            empty_locations = data['empty_locations']
            
            # Current logic counts empty locations as bins
            current_logic_bins = total_locations
            
            print(f"Rack {rack_key}:")
            print(f"  - Total locations: {total_locations}")
            print(f"  - Actual bins: {actual_bins}")
            print(f"  - Empty locations: {empty_locations}")
            print(f"  - Current logic shows: {current_logic_bins} bins")
            print(f"  - Discrepancy: {current_logic_bins - actual_bins} extra")
            print()
            
            # Show location details
            for loc in data['locations']:
                status = f"{loc['bin_count']} bins" if loc['bin_count'] > 0 else "EMPTY"
                print(f"    {loc['full_code']}: {status}")
            print()
    
    cursor.close()
    conn.close()

def analyze_specific_rack(rack_code):
    """Analyze a specific rack in detail"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print(f"=== DETAILED ANALYSIS FOR RACK {rack_code} ===\n")
    
    # Find locations that belong to this rack
    cursor.execute("""
        SELECT l.id, l.full_code, l.warehouse_id, w.name as warehouse_name
        FROM locations l
        JOIN warehouses w ON l.warehouse_id = w.id
        WHERE l.full_code LIKE %s
        ORDER BY l.full_code
    """, (f"{rack_code}%",))
    
    locations = cursor.fetchall()
    
    if not locations:
        print(f"No locations found for rack {rack_code}")
        return
    
    print(f"Found {len(locations)} locations for rack {rack_code}:")
    print()
    
    total_actual_bins = 0
    empty_locations = 0
    
    for location_id, full_code, warehouse_id, warehouse_name in locations:
        # Count bins for this location
        cursor.execute("""
            SELECT COUNT(*) 
            FROM bins 
            WHERE location_id = %s
        """, (location_id,))
        bin_count = cursor.fetchone()[0]
        
        # Get bin details if any exist
        if bin_count > 0:
            cursor.execute("""
                SELECT code 
                FROM bins 
                WHERE location_id = %s
                ORDER BY code
            """, (location_id,))
            bin_codes = [row[0] for row in cursor.fetchall()]
            bin_info = f"{bin_count} bins: {', '.join(bin_codes)}"
            total_actual_bins += bin_count
        else:
            bin_info = "EMPTY"
            empty_locations += 1
        
        print(f"  {full_code}: {bin_info}")
    
    print()
    print(f"Summary for rack {rack_code}:")
    print(f"  - Total locations: {len(locations)}")
    print(f"  - Actual bins: {total_actual_bins}")
    print(f"  - Empty locations: {empty_locations}")
    print(f"  - Current logic would show: {len(locations)} bins")
    print(f"  - Discrepancy: {len(locations) - total_actual_bins} extra")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("Bin Counting Analysis Tool")
    print("=" * 40)
    
    # Analyze all racks
    analyze_rack_bin_counts()
    
    # Analyze specific rack if provided
    import sys
    if len(sys.argv) > 1:
        rack_code = sys.argv[1]
        analyze_specific_rack(rack_code)
