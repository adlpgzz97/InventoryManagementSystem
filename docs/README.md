# Inventory Management System - API Documentation

## Overview
This document provides comprehensive API documentation for the Inventory Management System, including all endpoints, request/response formats, authentication, and usage examples.

## Table of Contents
1. [Authentication](#authentication)
2. [API Endpoints](#api-endpoints)
3. [Data Models](#data-models)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)

## Base URL
- **Development**: `http://localhost:5000`
- **Production**: `https://your-domain.com`

## Authentication
The API uses Flask-Login for session-based authentication.

### Login
```
POST /auth/login
```

### Logout
```
GET /auth/logout
```

### Protected Routes
Most API endpoints require authentication. Include session cookies in requests.

## API Endpoints

### Dashboard
- `GET /` - Main dashboard with system overview
- `GET /dashboard` - Dashboard data and statistics

### Products
- `GET /products` - List all products
- `POST /products` - Create new product
- `GET /products/<id>` - Get product details
- `PUT /products/<id>` - Update product
- `DELETE /products/<id>` - Delete product
- `POST /products/bulk-update` - Bulk update products
- `POST /products/bulk-delete` - Bulk delete products

### Stock Management
- `GET /stock` - List all stock items
- `POST /stock` - Add stock item
- `GET /stock/<id>` - Get stock item details
- `PUT /stock/<id>` - Update stock item
- `DELETE /stock/<id>` - Delete stock item
- `GET /stock/expiring` - Get expiring stock
- `GET /stock/low` - Get low stock items
- `POST /stock/reserve` - Reserve stock
- `POST /stock/release` - Release stock reservation

### Warehouses
- `GET /warehouses` - List all warehouses
- `POST /warehouses` - Create new warehouse
- `GET /warehouses/<id>` - Get warehouse details
- `PUT /warehouses/<id>` - Update warehouse
- `DELETE /warehouses/<id>` - Delete warehouse
- `GET /warehouses/<id>/stock` - Get warehouse stock summary

### Transactions
- `GET /transactions` - List all transactions
- `POST /transactions` - Create new transaction
- `GET /transactions/<id>` - Get transaction details
- `GET /transactions/type/<type>` - Get transactions by type
- `GET /transactions/date-range` - Get transactions by date range

### Scanner
- `GET /scanner` - Scanner interface
- `POST /scanner/scan` - Process barcode scan
- `GET /scanner/history` - Get scan history

## Data Models

### Product
```json
{
  "id": "uuid",
  "name": "string",
  "sku": "string",
  "description": "string",
  "dimensions": "string",
  "weight": "number",
  "picture_url": "string",
  "barcode": "string",
  "batch_tracked": "boolean",
  "created_at": "datetime"
}
```

### StockItem
```json
{
  "id": "uuid",
  "product_id": "uuid",
  "warehouse_id": "uuid",
  "bin_id": "uuid",
  "quantity": "number",
  "expiry_date": "datetime",
  "batch_number": "string",
  "created_at": "datetime"
}
```

### Warehouse
```json
{
  "id": "uuid",
  "name": "string",
  "code": "string",
  "address": "string",
  "contact_person": "string",
  "contact_email": "string",
  "contact_phone": "string",
  "parent_warehouse_id": "uuid",
  "created_at": "datetime"
}
```

### Transaction
```json
{
  "id": "uuid",
  "type": "string",
  "product_id": "uuid",
  "warehouse_id": "uuid",
  "quantity": "number",
  "user_id": "uuid",
  "notes": "string",
  "created_at": "datetime"
}
```

## Error Handling

### Standard Error Response
```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "datetime"
}
```

### Common Error Codes
- `VALIDATION_ERROR` - Input validation failed
- `NOT_FOUND` - Resource not found
- `UNAUTHORIZED` - Authentication required
- `FORBIDDEN` - Insufficient permissions
- `DATABASE_ERROR` - Database operation failed
- `SERVICE_ERROR` - Business logic error

## Rate Limiting
- **Default**: 100 requests per minute per IP
- **Authentication endpoints**: 10 requests per minute per IP
- **Bulk operations**: 20 requests per minute per authenticated user

## Examples

### Creating a Product
```bash
curl -X POST http://localhost:5000/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample Product",
    "sku": "SAMPLE-001",
    "description": "A sample product for testing",
    "dimensions": "10x5x2 cm",
    "weight": 0.5,
    "barcode": "1234567890123",
    "batch_tracked": false
  }'
```

### Getting Stock Items
```bash
curl -X GET http://localhost:5000/stock \
  -H "Cookie: session=your-session-cookie"
```

### Bulk Update Products
```bash
curl -X POST http://localhost:5000/products/bulk-update \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your-session-cookie" \
  -d '[
    {
      "id": "uuid-1",
      "name": "Updated Product 1"
    },
    {
      "id": "uuid-2",
      "name": "Updated Product 2"
    }
  ]'
```

## Testing
Use the provided test suite to verify API functionality:
```bash
python -m pytest backend/tests/ -v
```

## Support
For API support and questions, please refer to the main project documentation or create an issue in the project repository.
