from backend.app import create_app
from backend.models.stock import StockItem
import logging
logging.basicConfig(level=logging.INFO)

app = create_app()
print('Checking stock data structure...')

with app.app_context():
    try:
        stock_items = StockItem.get_all_with_locations()
        if stock_items:
            print('First stock item structure:')
            item = stock_items[0]
            print(f'Type: {type(item)}')
            print(f'Keys: {list(item.keys()) if hasattr(item, "keys") else "No keys method"}')
            print(f'Item: {item}')
            
            # Check if it has the properties the template expects
            print('\nTemplate expects these properties:')
            print(f'item.available_stock: {hasattr(item, "available_stock")}')
            print(f'item.product.name: {hasattr(item, "product")}')
            print(f'item.bin.code: {hasattr(item, "bin")}')
            
            # Check what properties are actually available
            print('\nActual properties available:')
            if hasattr(item, 'keys'):
                for key in item.keys():
                    print(f'  {key}: {item[key]}')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
