# Coding Standards - Inventory Management System

## Overview
This document outlines the coding standards and best practices for the Inventory Management System project. All developers must follow these standards to maintain code quality and consistency.

## Python Code Style

### General Principles
- **Readability**: Code should be self-documenting and easy to understand
- **Consistency**: Follow established patterns throughout the codebase
- **Simplicity**: Prefer simple, clear solutions over complex ones
- **Maintainability**: Write code that's easy to modify and extend

### Code Formatting

#### Line Length
- **Maximum line length**: 100 characters
- **Break long lines** at logical points (after operators, before opening parentheses)
- **Use parentheses** for line continuation when needed

```python
# Good
long_function_name(
    parameter1, parameter2, parameter3,
    parameter4, parameter5
)

# Bad
long_function_name(parameter1, parameter2, parameter3, parameter4, parameter5)
```

#### Indentation
- **Use 4 spaces** for indentation (never tabs)
- **Be consistent** with indentation levels
- **Align continuation lines** with opening delimiter

```python
# Good
def long_function_name(
        parameter1, parameter2,
        parameter3, parameter4):
    print(parameter1)

# Bad
def long_function_name(
    parameter1, parameter2,
    parameter3, parameter4):
        print(parameter1)
```

#### Imports
- **Group imports** in the following order:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- **Separate groups** with blank lines
- **Use absolute imports** for local modules
- **Avoid wildcard imports** (`from module import *`)

```python
# Good
import os
import sys
from typing import Dict, List, Optional

import flask
from flask_login import login_required

from backend.models.product import Product
from backend.services.product_service import ProductService

# Bad
from backend.models import *
import flask, os, sys
```

### Naming Conventions

#### Variables and Functions
- **Use snake_case** for variables and functions
- **Use descriptive names** that explain the purpose
- **Avoid single-letter names** except for loop counters

```python
# Good
def calculate_total_inventory():
    inventory_count = 0
    for product in products:
        inventory_count += product.quantity
    return inventory_count

# Bad
def calc():
    c = 0
    for p in ps:
        c += p.q
    return c
```

#### Classes
- **Use PascalCase** for class names
- **Use descriptive names** that represent the entity

```python
# Good
class ProductInventoryManager:
    pass

class StockTransaction:
    pass

# Bad
class Manager:
    pass

class Data:
    pass
```

#### Constants
- **Use UPPER_SNAKE_CASE** for constants
- **Define constants** at module level

```python
# Good
MAX_PRODUCT_NAME_LENGTH = 255
DEFAULT_WAREHOUSE_CODE = "WH-001"
SUPPORTED_FILE_TYPES = ['.jpg', '.png', '.pdf']

# Bad
maxProductNameLength = 255
default_warehouse_code = "WH-001"
```

### Function and Method Design

#### Function Length
- **Keep functions under 20 lines** when possible
- **Break large functions** into smaller, focused functions
- **Single responsibility**: Each function should do one thing well

```python
# Good - Small, focused function
def validate_product_name(name: str) -> bool:
    if not name or len(name.strip()) == 0:
        return False
    if len(name) > MAX_PRODUCT_NAME_LENGTH:
        return False
    return True

# Bad - Function doing too many things
def process_product_data(product_data):
    # 50+ lines of mixed validation, processing, and database operations
    pass
```

#### Parameters
- **Limit parameters** to 5 or fewer
- **Use keyword arguments** for clarity
- **Provide default values** when appropriate

```python
# Good
def create_product(
    name: str,
    sku: str,
    description: Optional[str] = None,
    weight: Optional[float] = None
) -> Product:
    pass

# Bad
def create_product(name, sku, description, weight, category, supplier, price, cost, barcode, dimensions, picture_url, batch_tracked):
    pass
```

#### Return Values
- **Be consistent** with return types
- **Use type hints** for clarity
- **Return early** when possible

```python
# Good
def get_product_by_id(product_id: str) -> Optional[Product]:
    if not product_id:
        return None
    
    try:
        return Product.query.get(product_id)
    except Exception:
        return None

# Bad
def get_product_by_id(product_id):
    if product_id:
        try:
            product = Product.query.get(product_id)
            if product:
                return product
            else:
                return None
        except Exception:
            return None
    else:
        return None
```

### Error Handling

#### Exception Handling
- **Use specific exceptions** rather than generic ones
- **Catch exceptions** at the appropriate level
- **Log errors** with context information
- **Don't suppress exceptions** without good reason

```python
# Good
def get_product_by_id(product_id: str) -> Optional[Product]:
    try:
        return Product.query.get(product_id)
    except DatabaseConnectionError as e:
        logger.error(f"Database connection failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting product {product_id}: {e}")
        raise

# Bad
def get_product_by_id(product_id: str):
    try:
        return Product.query.get(product_id)
    except:
        pass
```

#### Validation
- **Validate input** at function boundaries
- **Use custom exceptions** for validation errors
- **Provide clear error messages**

```python
# Good
def create_product(product_data: Dict[str, Any]) -> Product:
    if not product_data.get('name'):
        raise ValidationError("Product name is required")
    
    if not product_data.get('sku'):
        raise ValidationError("Product SKU is required")
    
    # Process valid data...
    pass

# Bad
def create_product(product_data):
    # Process data without validation
    pass
```

### Database Operations

#### Query Patterns
- **Use parameterized queries** to prevent SQL injection
- **Handle database errors** gracefully
- **Use transactions** for multi-step operations
- **Close connections** properly

```python
# Good
def get_products_by_category(category: str) -> List[Product]:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM products WHERE category = %s",
                    (category,)
                )
                return cursor.fetchall()
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise

# Bad
def get_products_by_category(category):
    cursor.execute(f"SELECT * FROM products WHERE category = '{category}'")
    return cursor.fetchall()
```

### Testing Standards

#### Test Structure
- **Use descriptive test names** that explain what is being tested
- **Follow AAA pattern**: Arrange, Act, Assert
- **Test one thing** per test method
- **Use meaningful test data**

```python
# Good
def test_create_product_with_valid_data_should_succeed():
    # Arrange
    product_data = {
        'name': 'Test Product',
        'sku': 'TEST-001',
        'description': 'A test product'
    }
    
    # Act
    result = product_service.create_product(product_data)
    
    # Assert
    assert result['success'] is True
    assert result['data']['name'] == 'Test Product'

# Bad
def test_create():
    result = product_service.create_product({})
    assert result
```

#### Test Coverage
- **Aim for 90%+ coverage** of business logic
- **Test edge cases** and error conditions
- **Mock external dependencies** in unit tests
- **Use test fixtures** for common setup

### Documentation Standards

#### Docstrings
- **Use Google-style docstrings** for all public functions and classes
- **Include parameter descriptions** and return values
- **Document exceptions** that may be raised

```python
def create_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new product in the system.
    
    Args:
        product_data: Dictionary containing product information.
            Must include 'name' and 'sku' fields.
            
    Returns:
        Dictionary with 'success' flag and product data or error message.
        
    Raises:
        ValidationError: If required fields are missing or invalid.
        DatabaseError: If database operation fails.
    """
    pass
```

#### Comments
- **Explain why**, not what
- **Keep comments up-to-date** with code changes
- **Use clear, concise language**
- **Avoid obvious comments**

```python
# Good
# Skip validation for system-generated products
if product.is_system_generated:
    return True

# Bad
# Check if product is system generated
if product.is_system_generated:
    return True
```

### Security Standards

#### Input Validation
- **Validate all user input** before processing
- **Sanitize data** to prevent injection attacks
- **Use parameterized queries** for database operations
- **Validate file uploads** and file types

#### Authentication and Authorization
- **Never store passwords** in plain text
- **Use secure session management**
- **Implement proper access controls**
- **Log security events**

### Performance Standards

#### Database Queries
- **Optimize database queries** for performance
- **Use appropriate indexes** on database tables
- **Avoid N+1 query problems**
- **Use connection pooling** for database connections

#### Memory Management
- **Avoid memory leaks** by properly closing resources
- **Use generators** for large datasets
- **Limit memory usage** in loops and iterations

### Code Review Checklist

Before submitting code for review, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Code coverage meets requirements
- [ ] Documentation is updated
- [ ] Error handling is implemented
- [ ] Security considerations are addressed
- [ ] Performance impact is considered
- [ ] No debugging code remains
- [ ] Logging is appropriate

### Tools and Automation

#### Code Quality Tools
- **Flake8**: Code linting and style checking
- **Black**: Code formatting
- **isort**: Import sorting
- **MyPy**: Type checking
- **Pytest**: Testing framework
- **Coverage.py**: Code coverage

#### Pre-commit Hooks
- **Install pre-commit**: `pip install pre-commit`
- **Install hooks**: `pre-commit install`
- **Run manually**: `pre-commit run --all-files`

### Continuous Integration

#### Automated Checks
- **Style checking** runs on every commit
- **Unit tests** must pass before merge
- **Code coverage** reports are generated
- **Security scans** are performed

#### Quality Gates
- **Minimum coverage**: 90%
- **No critical security issues**
- **All style checks pass**
- **All tests pass**

## Conclusion

Following these coding standards ensures:
- **Consistent code quality** across the project
- **Easier maintenance** and debugging
- **Better collaboration** between team members
- **Reduced technical debt**
- **Improved security** and reliability

All team members are responsible for following these standards and maintaining code quality.
