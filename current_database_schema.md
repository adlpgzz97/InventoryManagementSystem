# Current Database Schema

## INVENTORY DATABASE SCHEMA OVERVIEW
==================================================

**Total Tables:** 7  
**Total Columns:** 36  
**Total Foreign Keys:** 5  
**Total Rows:** 15

---

## TABLE: LOCATIONS
**Rows:** 4  
**Columns:** 4  
**Foreign Keys:** 1

### COLUMNS:
- `id` (uuid) NOT NULL DEFAULT uuid_generate_v4() [PRIMARY KEY]
- `warehouse_id` (uuid) NULL [FK -> warehouses.id]
- `aisle` (text) NOT NULL
- `bin` (text) NOT NULL

### FOREIGN KEYS:
- `warehouse_id` -> `warehouses.id` (locations_warehouse_id_fkey)

### CHECK CONSTRAINTS:
- `2200_32848_1_not_null`: id IS NOT NULL
- `2200_32848_3_not_null`: aisle IS NOT NULL
- `2200_32848_4_not_null`: bin IS NOT NULL

---

## TABLE: ORDERS
**Rows:** 0  
**Columns:** 4

### COLUMNS:
- `id` (uuid) NOT NULL DEFAULT uuid_generate_v4() [PRIMARY KEY]
- `client_id` (uuid) NULL
- `status` (text) NOT NULL
- `created_at` (timestamp without time zone) NULL DEFAULT now()

### CHECK CONSTRAINTS:
- `orders_status_check`: (status = ANY (ARRAY['open'::text, 'fulfilled'::text, 'cancelled'::text]))
- `2200_32883_1_not_null`: id IS NOT NULL
- `2200_32883_3_not_null`: status IS NOT NULL

---

## TABLE: PRODUCTS
**Rows:** 3  
**Columns:** 9

### COLUMNS:
- `id` (uuid) NOT NULL DEFAULT uuid_generate_v4() [PRIMARY KEY]
- `sku` (text) NOT NULL
- `name` (text) NOT NULL
- `description` (text) NULL
- `dimensions` (text) NULL
- `weight` (numeric) NULL
- `picture_url` (text) NULL
- `barcode` (text) NULL
- `created_at` (timestamp without time zone) NULL DEFAULT now()

### CHECK CONSTRAINTS:
- `2200_32829_1_not_null`: id IS NOT NULL
- `2200_32829_2_not_null`: sku IS NOT NULL
- `2200_32829_3_not_null`: name IS NOT NULL

---

## TABLE: RESERVATIONS
**Rows:** 0  
**Columns:** 6  
**Foreign Keys:** 2

### COLUMNS:
- `id` (uuid) NOT NULL DEFAULT uuid_generate_v4() [PRIMARY KEY]
- `order_id` (uuid) NULL [FK -> orders.id]
- `product_id` (uuid) NULL [FK -> products.id]
- `qty` (integer) NOT NULL
- `status` (text) NOT NULL
- `created_at` (timestamp without time zone) NULL DEFAULT now()

### FOREIGN KEYS:
- `order_id` -> `orders.id` (reservations_order_id_fkey)
- `product_id` -> `products.id` (reservations_product_id_fkey)

### CHECK CONSTRAINTS:
- `reservations_status_check`: (status = ANY (ARRAY['reserved'::text, 'picked'::text, 'cancelled'::text]))
- `2200_32893_1_not_null`: id IS NOT NULL
- `2200_32893_4_not_null`: qty IS NOT NULL
- `2200_32893_5_not_null`: status IS NOT NULL

---

## TABLE: STOCK_ITEMS
**Rows:** 3  
**Columns:** 5  
**Foreign Keys:** 2

### COLUMNS:
- `id` (uuid) NOT NULL DEFAULT uuid_generate_v4() [PRIMARY KEY]
- `product_id` (uuid) NULL [FK -> products.id]
- `location_id` (uuid) NULL [FK -> locations.id]
- `qty_available` (integer) NOT NULL DEFAULT 0
- `qty_reserved` (integer) NOT NULL DEFAULT 0

### FOREIGN KEYS:
- `product_id` -> `products.id` (stock_items_product_id_fkey)
- `location_id` -> `locations.id` (stock_items_location_id_fkey)

### CHECK CONSTRAINTS:
- `stock_items_qty_available_check`: (qty_available >= 0)
- `stock_items_qty_reserved_check`: (qty_reserved >= 0)
- `2200_32863_1_not_null`: id IS NOT NULL
- `2200_32863_4_not_null`: qty_available IS NOT NULL
- `2200_32863_5_not_null`: qty_reserved IS NOT NULL

---

## TABLE: USERS
**Rows:** 3  
**Columns:** 5

### COLUMNS:
- `id` (uuid) NOT NULL DEFAULT uuid_generate_v4() [PRIMARY KEY]
- `username` (text) NOT NULL
- `password_hash` (text) NOT NULL
- `role` (text) NOT NULL
- `created_at` (timestamp without time zone) NULL DEFAULT now()

### CHECK CONSTRAINTS:
- `users_role_check`: (role = ANY (ARRAY['admin'::text, 'manager'::text, 'worker'::text]))
- `2200_32817_1_not_null`: id IS NOT NULL
- `2200_32817_2_not_null`: username IS NOT NULL
- `2200_32817_3_not_null`: password_hash IS NOT NULL
- `2200_32817_4_not_null`: role IS NOT NULL

---

## TABLE: WAREHOUSES
**Rows:** 2  
**Columns:** 3

### COLUMNS:
- `id` (uuid) NOT NULL DEFAULT uuid_generate_v4() [PRIMARY KEY]
- `name` (text) NOT NULL
- `address` (text) NULL

### CHECK CONSTRAINTS:
- `2200_32840_1_not_null`: id IS NOT NULL
- `2200_32840_2_not_null`: name IS NOT NULL

---

## Missing Features Compared to Demo App:
1. **Batch Tracking**: Missing `batch_tracked` column in products table
2. **Batch Information**: Missing `batch_id`, `expiry_date`, `received_date` columns in stock_items table
3. **Audit Trail**: Missing `stock_transactions` table
4. **Stock Movement Functions**: Missing stored procedures for stock operations
