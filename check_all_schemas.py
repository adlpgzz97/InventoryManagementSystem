from backend.utils.database import execute_query
import logging
logging.basicConfig(level=logging.INFO)

print('Checking all table schemas...')

tables = ['stock_items', 'products', 'bins', 'locations', 'warehouses', 'users']

for table in tables:
    print(f'\n=== {table.upper()} TABLE ===')
    try:
        # Check the actual schema of each table
        schema = execute_query('''
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = %s 
            ORDER BY ordinal_position
        ''', (table,), fetch_all=True)
        
        if schema:
            print('Columns:')
            for col in schema:
                nullable = 'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'
                print(f'  {col["column_name"]}: {col["data_type"]} ({nullable})')
        else:
            print('Table not found or no columns')
            
    except Exception as e:
        print(f'Error checking {table}: {e}')
