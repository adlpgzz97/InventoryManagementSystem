# Stock Functionality Fix Summary

## Issue Description
The add stock and edit stock functionalities were not working due to the restructuring of the location and bin data. The system had been updated to use a new hierarchical structure where:
- Stock items link to `bins.id` (not `locations.id`)
- Locations use `full_code` (not `aisle`/`bin` fields)
- Bins are independent entities that can be assigned to locations

## Root Cause Analysis
1. **Data Structure Mismatch**: Stock items were still referencing `location_id` instead of `bin_id`
2. **Frontend Display Issues**: Templates were showing location dropdowns instead of bin dropdowns
3. **PostgREST Dependency**: The add stock function was failing because PostgREST was not running, causing "no products available" despite having 17 products in the database

## Fixes Applied

### 1. Backend Changes (`backend/app.py`)

#### `add_stock` function (lines 2234-2300)
- **Before**: Used PostgREST to fetch products and locations
- **After**: Uses direct database queries for both products and bins
- **Key Changes**:
  ```python
  # Before
  products_data = postgrest_request('products?select=id,sku,name')
  # locations_data = postgrest_request('locations?select=id,aisle,bin,warehouses(name)')
  
  # After
  cur.execute("SELECT id, sku, name, barcode FROM products ORDER BY name")
  products_data = cur.fetchall()
  
  cur.execute("""
      SELECT b.id, b.code, l.full_code, w.name as warehouse_name
      FROM bins b
      LEFT JOIN locations l ON b.location_id = l.id
      LEFT JOIN warehouses w ON l.warehouse_id = w.id
      ORDER BY w.name, l.full_code, b.code
  """)
  ```

#### `handle_stock_receiving` function (lines 148-247)
- **Before**: Used `location_id` for all stock operations
- **After**: Uses `bin_id` for all stock operations
- **Key Changes**:
  ```python
  # Before
  def handle_stock_receiving(product_id, location_id, qty_available, ...):
      INSERT INTO stock_items (product_id, location_id, ...)
      SELECT * FROM stock_items WHERE product_id = %s AND location_id = %s
  
  # After
  def handle_stock_receiving(product_id, bin_id, qty_available, ...):
      INSERT INTO stock_items (product_id, bin_id, ...)
      SELECT * FROM stock_items WHERE product_id = %s AND bin_id = %s
  ```

#### `edit_stock` function (lines 1694-1793)
- **Before**: Used PostgREST and `location_id` references
- **After**: Uses direct database queries and `bin_id` references
- **Key Changes**:
  ```python
  # Before
  data = {'location_id': request.form.get('location_id')}
  stock_data = postgrest_request(f'stock_items?id=eq.{stock_id}&select=*')
  products_data = postgrest_request('products?select=id,sku,name')
  
  # After
  data = {'bin_id': request.form.get('bin_id')}
  cur.execute("""
      SELECT si.*, b.code as bin_code, l.full_code, w.name as warehouse_name
      FROM stock_items si
      LEFT JOIN bins b ON si.bin_id = b.id
      LEFT JOIN locations l ON b.location_id = l.id
      LEFT JOIN warehouses w ON l.warehouse_id = w.id
      WHERE si.id = %s
  """, (stock_id,))
  cur.execute("SELECT id, sku, name, barcode FROM products ORDER BY name")
  ```

### 2. Frontend Changes

#### `add_stock_modal.html`
- **Before**: Location dropdown with `location_id`
- **After**: Storage bin dropdown with `bin_id`
- **Key Changes**:
  ```html
  <!-- Before -->
  <label for="location_id" class="form-label">Location</label>
  <select class="form-select" id="location_id" name="location_id" required>
      <option value="">Select Location</option>
      {% for location in locations %}
      <option value="{{ location.id }}">{{ location.warehouse_name }} - {{ location.full_code }}</option>
      {% endfor %}
  </select>
  
  <!-- After -->
  <label for="bin_id" class="form-label">Storage Bin <span class="text-danger">*</span></label>
  <select class="form-select" id="bin_id" name="bin_id" required>
      <option value="">Select Storage Bin</option>
      {% for bin in bins %}
      <option value="{{ bin.id }}">{{ bin.display_name }}</option>
      {% endfor %}
  </select>
  ```

#### `edit_stock_modal.html`
- **Before**: Location dropdown with `location_id`
- **After**: Storage bin dropdown with `bin_id`
- **Key Changes**:
  ```html
  <!-- Before -->
  <label for="location_id" class="form-label">Location</label>
  <select class="form-select" id="location_id" name="location_id" required>
      <option value="">Select Location</option>
      {% for location in locations %}
      <option value="{{ location.id }}" {% if location.id == stock.location_id %}selected{% endif %}>
          {{ location.warehouse_name }} - {{ location.full_code }}
      </option>
      {% endfor %}
  </select>
  
  <!-- After -->
  <label for="bin_id" class="form-label">Storage Bin <span class="text-danger">*</span></label>
  <select class="form-select" id="bin_id" name="bin_id" required>
      <option value="">Select Storage Bin</option>
      {% for bin in bins %}
      <option value="{{ bin.id }}" {% if bin.id == stock.bin_id %}selected{% endif %}>
          {{ bin.display_name }}
      </option>
      {% endfor %}
  </select>
  ```

### 3. PostgREST Configuration Fix
- **Issue**: PostgREST was not running due to incorrect database credentials
- **Fix**: Updated `db/postgrest.conf` with correct database connection string
- **Alternative**: Replaced PostgREST calls with direct database queries for better reliability

## Data Structure Alignment

### New Stock Item Flow
```
Stock Item → Bin → Location → Warehouse
```

### Database Relationships
- `stock_items.bin_id` → `bins.id`
- `bins.location_id` → `locations.id`
- `locations.warehouse_id` → `warehouses.id`

### Display Format
- **Bin Display**: `{Warehouse Name} - {Location Code} - {Bin Code}`
- **Example**: `Main Warehouse - A2F10 - BIN001`

## Testing Results
- ✅ Add stock modal loads successfully (HTTP 200)
- ✅ Products are fetched directly from database (17 products available)
- ✅ Bins are fetched with proper hierarchical information
- ✅ Edit stock functionality uses correct bin references
- ✅ Stock receiving logic handles bin-based operations correctly

## Benefits of the Fix
1. **Reliability**: Direct database queries eliminate PostgREST dependency issues
2. **Performance**: Faster data fetching without HTTP overhead
3. **Consistency**: All stock operations now use the correct bin-based structure
4. **User Experience**: Clear display of warehouse → location → bin hierarchy
5. **Maintainability**: Simplified code structure with fewer external dependencies

## Files Modified
- `backend/app.py` - Updated add_stock, edit_stock, and handle_stock_receiving functions
- `backend/views/add_stock_modal.html` - Updated to use bin dropdown
- `backend/views/edit_stock_modal.html` - Updated to use bin dropdown
- `db/postgrest.conf` - Fixed database credentials

## Next Steps
The stock functionality should now work correctly. Users can:
1. Add new stock items by selecting products and storage bins
2. Edit existing stock items with proper bin assignments
3. View stock items with clear warehouse → location → bin hierarchy
4. Experience faster modal loading without PostgREST dependency issues
