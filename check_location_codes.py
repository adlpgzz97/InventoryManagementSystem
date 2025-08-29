#!/usr/bin/env python3

import psycopg2
import os

def check_location_codes():
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
        
        # Check all locations
        cur.execute('SELECT id, warehouse_id, full_code FROM locations LIMIT 10')
        results = cur.fetchall()
        print('All locations in database:')
        for result in results:
            print(f'  ID: {result[0]}, Warehouse: {result[1]}, Code: {result[2]}')
        
        # Check warehouses
        cur.execute('SELECT id, name, code FROM warehouses LIMIT 5')
        warehouse_results = cur.fetchall()
        print('\nWarehouses:')
        for result in warehouse_results:
            print(f'  ID: {result[0]}, Name: {result[1]}, Code: {result[2]}')
        
        # Check bins
        cur.execute('SELECT id, code, location_id FROM bins LIMIT 10')
        bin_results = cur.fetchall()
        print('\nBins:')
        for result in bin_results:
            print(f'  ID: {result[0]}, Code: {result[1]}, Location: {result[2]}')
        
        cur.close()
        conn.close()
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    check_location_codes()
