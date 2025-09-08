from backend.app import create_app
from backend.services.product_service import ProductService
import logging
logging.basicConfig(level=logging.INFO)

app = create_app()
print('Testing ProductService data structure...')

with app.app_context():
    try:
        product_service = ProductService()
        products = product_service.search_products('')
        
        if products:
            print('First product structure:')
            product = products[0]
            print(f'Type: {type(product)}')
            print(f'Product: {product}')
            
            # Check if it has the properties the template might expect
            print('\nTemplate might expect these properties:')
            print(f'product.name: {hasattr(product, "name")}')
            print(f'product.sku: {hasattr(product, "sku")}')
            print(f'product.description: {hasattr(product, "description")}')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
