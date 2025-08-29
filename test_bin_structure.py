#!/usr/bin/env python3

import psycopg2

def test_bin_structure():
    """Test the bin structure for hierarchical view"""
    
    try:
        # Database connection parameters
        db_config = {
            'host': 'localhost',
            'port': '5432',
            'database': 'inventory_db',
            'user': 'postgres',
            'password': 'TatUtil97=='
        }
        
        # Connect to database
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Test the bin structure for a few locations
        test_locations = ['A1F4', 'B1B1', 'C1A1']
        
        print("Testing bin structure for hierarchical view:")
        print("=" * 60)
        
        for location_code in test_locations:
            print(f"\nLocation: {location_code}")
            
            # Get bins for this location
            cur.execute("""
                SELECT b.code, b.id, 
                       COUNT(si.id) as stock_count,
                       COALESCE(SUM(si.on_hand), 0) as total_quantity
                FROM locations l
                LEFT JOIN bins b ON l.id = b.location_id
                LEFT JOIN stock_items si ON b.id = si.bin_id
                WHERE l.full_code = %s
                GROUP BY b.code, b.id
                ORDER BY b.code
            """, (location_code,))
            
            results = cur.fetchall()
            
            if results:
                for result in results:
                    bin_code, bin_id, stock_count, total_quantity = result
                    occupied = "Yes" if total_quantity > 0 else "No"
                    print(f"  Bin: {bin_code} (ID: {bin_id})")
                    print(f"    Stock Items: {stock_count}")
                    print(f"    Total Quantity: {total_quantity}")
                    print(f"    Occupied: {occupied}")
            else:
                print(f"  No bins found for location {location_code}")
        
        # Show some statistics
        print(f"\n" + "=" * 60)
        print("Overall Statistics:")
        
        # Total bins
        cur.execute("SELECT COUNT(*) FROM bins")
        total_bins = cur.fetchone()[0]
        print(f"Total Bins: {total_bins}")
        
        # Occupied bins
        cur.execute("""
            SELECT COUNT(DISTINCT b.id)
            FROM bins b
            JOIN stock_items si ON b.id = si.bin_id
            WHERE si.on_hand > 0
        """)
        occupied_bins = cur.fetchone()[0]
        print(f"Occupied Bins: {occupied_bins}")
        
        # Empty bins
        empty_bins = total_bins - occupied_bins
        print(f"Empty Bins: {empty_bins}")
        
        # Utilization percentage
        utilization = (occupied_bins / total_bins * 100) if total_bins > 0 else 0
        print(f"Utilization: {utilization:.1f}%")
        
        cur.close()
        conn.close()
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    test_bin_structure()
