"""
Inventory Management App - Flask Backend
Main Flask application entry point
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import psycopg2
import psycopg2.extras

import bcrypt
import requests
import os
import json
import uuid
from datetime import datetime

app = Flask(__name__, template_folder='views')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Custom Jinja2 filter to group locations into ranges
@app.template_filter('group_locations')
def group_locations(locations):
    """
    Group consecutive locations into ranges.
    Example: [A1, A2, A3, A4, A5, B1, B2, B3, B4, C1, C2] 
    becomes: ['A1-A5', 'B1-B4', 'C1-C2']
    """
    if not locations:
        return []
    
    # Sort locations by aisle and bin
    sorted_locations = sorted(locations, key=lambda x: (x['aisle'], int(x['bin']) if x['bin'].isdigit() else x['bin']))
    
    ranges = []
    current_range = None
    
    for location in sorted_locations:
        aisle = location['aisle']
        bin_num = location['bin']
        
        if current_range is None:
            # Start new range
            current_range = {'aisle': aisle, 'start': bin_num, 'end': bin_num}
        elif current_range['aisle'] == aisle:
            # Same aisle, check if consecutive
            try:
                current_bin = int(bin_num)
                end_bin = int(current_range['end'])
                if current_bin == end_bin + 1:
                    # Consecutive, extend range
                    current_range['end'] = bin_num
                else:
                    # Not consecutive, finish current range and start new one
                    if current_range['start'] == current_range['end']:
                        ranges.append(f"{current_range['aisle']}{current_range['start']}")
                    else:
                        ranges.append(f"{current_range['aisle']}{current_range['start']}-{current_range['end']}")
                    current_range = {'aisle': aisle, 'start': bin_num, 'end': bin_num}
            except ValueError:
                # Non-numeric bin, treat as separate
                if current_range['start'] == current_range['end']:
                    ranges.append(f"{current_range['aisle']}{current_range['start']}")
                else:
                    ranges.append(f"{current_range['aisle']}{current_range['start']}-{current_range['end']}")
                current_range = {'aisle': aisle, 'start': bin_num, 'end': bin_num}
        else:
            # Different aisle, finish current range and start new one
            if current_range['start'] == current_range['end']:
                ranges.append(f"{current_range['aisle']}{current_range['start']}")
            else:
                ranges.append(f"{current_range['aisle']}{current_range['start']}-{current_range['end']}")
            current_range = {'aisle': aisle, 'start': bin_num, 'end': bin_num}
    
    # Add the last range
    if current_range:
        if current_range['start'] == current_range['end']:
            ranges.append(f"{current_range['aisle']}{current_range['start']}")
        else:
            ranges.append(f"{current_range['aisle']}{current_range['start']}-{current_range['end']}")
    
    return ranges

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'inventory_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'TatUtil97==')
}

# PostgREST configuration
POSTGREST_URL = os.environ.get('POSTGREST_URL', 'http://localhost:3000')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, username, role FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(str(user_data['id']), user_data['username'], user_data['role'])
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def postgrest_request(endpoint, method='GET', data=None):
    """Make request to PostgREST API"""
    url = f"{POSTGREST_URL}/{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        
        return response.json() if response.content else {}
    except Exception as e:
        print(f"PostgREST request error: {e}")
        return None

def handle_stock_receiving(product_id, location_id, qty_available, qty_reserved=0, batch_id=None, expiry_date=None):
    """
    Handle stock receiving with batch tracking logic.
    For non-batch-tracked products: combine stock in same location
    For batch-tracked products: create separate inventory record
    """
    try:
        # Get product information to check if it's batch tracked using direct SQL
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT batch_tracked FROM products WHERE id = %s", (product_id,))
        product_data = cur.fetchone()
        
        if not product_data:
            cur.close()
            conn.close()
            raise Exception("Product not found")
        
        is_batch_tracked = product_data.get('batch_tracked', False)
        
        if is_batch_tracked:
            # For batch-tracked products, always create new record
            cur.execute("""
                INSERT INTO stock_items (product_id, location_id, on_hand, qty_reserved, batch_id, expiry_date)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (product_id, location_id, qty_available, qty_reserved, batch_id, expiry_date))
            
            stock_id = cur.fetchone()['id']
            conn.commit()
            cur.close()
            conn.close()
            
            # Log transaction
            log_stock_transaction(stock_id, 'receive', qty_available, 0, qty_available)
            
            return {'id': stock_id}
        else:
            # For non-batch-tracked products, check if stock already exists in this location
            cur.execute("""
                SELECT * FROM stock_items 
                WHERE product_id = %s AND location_id = %s
            """, (product_id, location_id))
            existing_stock = cur.fetchone()
            
            if existing_stock:
                # Combine with existing stock
                new_available = existing_stock['on_hand'] + qty_available
                new_reserved = existing_stock['qty_reserved'] + qty_reserved
                
                cur.execute("""
                    UPDATE stock_items 
                    SET on_hand = %s, qty_reserved = %s 
                    WHERE id = %s
                """, (new_available, new_reserved, existing_stock['id']))
                
                conn.commit()
                cur.close()
                conn.close()
                
                # Log transaction
                log_stock_transaction(
                    existing_stock['id'], 'receive', qty_available, 
                    existing_stock['on_hand'], new_available
                )
                
                return {'id': existing_stock['id']}
            else:
                # Create new stock record (no batch info for non-batch-tracked)
                cur.execute("""
                    INSERT INTO stock_items (product_id, location_id, on_hand, qty_reserved, batch_id, expiry_date)
                    VALUES (%s, %s, %s, %s, NULL, NULL) RETURNING id
                """, (product_id, location_id, qty_available, qty_reserved))
                
                stock_id = cur.fetchone()['id']
                conn.commit()
                cur.close()
                conn.close()
                
                # Log transaction
                log_stock_transaction(stock_id, 'receive', qty_available, 0, qty_available)
                
                return {'id': stock_id}
    except Exception as e:
        print(f"Error handling stock receiving: {e}")
        raise e

def log_stock_transaction(stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, 
                         reference_id=None, notes=None, user_id=None):
    """Log stock transaction for audit trail"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO stock_transactions 
            (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, reference_id, notes, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, reference_id, notes, user_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging stock transaction: {e}")
        return None

@app.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT id, username, password_hash, role FROM users WHERE username = %s", (username,))
            user_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                user = User(str(user_data['id']), user_data['username'], user_data['role'])
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
        except Exception as e:
            flash(f'Login error: {e}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get counts
        cur.execute("SELECT COUNT(*) as count FROM products")
        total_products = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM warehouses")
        total_warehouses = cur.fetchone()['count']
        
        # Get stock data with product and bin information
        cur.execute("""
            SELECT 
                si.*,
                p.name as product_name, 
                p.sku as product_sku,
                b.code as bin_code,
                l.full_code,
                w.name as warehouse_name
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            ORDER BY si.created_at DESC
            LIMIT 10
        """)
        stock_data_raw = cur.fetchall()
        cur.close()
        conn.close()
        
        # Format the data to match the template expectations
        stock_data = []
        for item in stock_data_raw:
            item_dict = dict(item)
            # Create nested structure for template compatibility
            item_dict['products'] = {
                'name': item_dict.get('product_name', 'Unknown'),
                'sku': item_dict.get('product_sku', 'N/A')
            }
            item_dict['locations'] = {
                'full_code': item_dict.get('full_code', ''),
                'bin_code': item_dict.get('bin_code', ''),
                'warehouses': {
                    'name': item_dict.get('warehouse_name', 'Unknown')
                }
            }
            stock_data.append(item_dict)
        
        # Calculate low stock items
        low_stock_items = [item for item in stock_data if item['on_hand'] < 10]
        
        return render_template('dashboard.html', 
                             stock_data=stock_data,
                             total_products=total_products,
                             total_warehouses=total_warehouses,
                             low_stock_count=len(low_stock_items))
    except Exception as e:
        flash(f'Error loading dashboard: {e}', 'error')
        return render_template('dashboard.html', stock_data=[], total_products=0, 
                             total_warehouses=0, low_stock_count=0)

@app.route('/products')
@login_required
def products():
    """Products listing"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get products with stock totals and replenishment policies
        cur.execute("""
            SELECT 
                p.*,
                COALESCE(SUM(si.on_hand), 0) as available_stock,
                COALESCE(SUM(si.on_hand + si.qty_reserved), 0) as total_stock,
                rp.forecasting_mode,
                rp.manual_reorder_point,
                rp.manual_safety_stock,
                rp.manual_lead_time_days,
                rp.forecasting_notes
            FROM products p
            LEFT JOIN stock_items si ON p.id = si.product_id
            LEFT JOIN replenishment_policies rp ON p.id = rp.product_id
            GROUP BY p.id, p.sku, p.name, p.description, p.dimensions, p.weight, 
                     p.barcode, p.picture_url, p.batch_tracked, p.created_at,
                     rp.forecasting_mode, rp.manual_reorder_point, rp.manual_safety_stock,
                     rp.manual_lead_time_days, rp.forecasting_notes
            ORDER BY p.created_at DESC
        """)
        products_data = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to list of dicts
        products_list = [dict(row) for row in products_data] if products_data else []
        
        return render_template('products.html', products=products_list)
    except Exception as e:
        flash(f'Error loading products: {e}', 'error')
        return render_template('products.html', products=[])

@app.route('/stock')
@login_required
def stock():
    """Stock overview"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get stock items with product and bin information
        cur.execute("""
            SELECT 
                si.*,
                p.name as product_name, 
                p.sku as product_sku,
                b.code as bin_code,
                l.full_code,
                w.name as warehouse_name
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            ORDER BY si.created_at DESC
        """)
        stock_data = cur.fetchall()
        cur.close()
        conn.close()
        
        # Format the data to match the template expectations
        stock_list = []
        for item in stock_data:
            item_dict = dict(item)
            
            # Use the actual bin code from the bins table
            bin_code = item_dict.get('bin_code', '')
            full_code = item_dict.get('full_code', '')
            
            # Location code should show the full location code
            location_code = full_code
            
            # Create nested structure for template compatibility
            item_dict['products'] = {
                'name': item_dict.get('product_name', 'Unknown'),
                'sku': item_dict.get('product_sku', 'N/A')
            }
            item_dict['locations'] = {
                'full_code': item_dict.get('full_code', ''),
                'bin_code': bin_code,
                'location_code': location_code,
                'warehouses': {
                    'name': item_dict.get('warehouse_name', 'Unknown')
                }
            }
            stock_list.append(item_dict)
        
        return render_template('stock.html', stock_items=stock_list)
    except Exception as e:
        flash(f'Error loading stock: {e}', 'error')
        return render_template('stock.html', stock_items=[])

@app.route('/warehouses')
@login_required
def warehouses():
    """Warehouses listing"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get warehouses with location counts
        cur.execute("""
            SELECT w.*, COUNT(l.id) as location_count
            FROM warehouses w
            LEFT JOIN locations l ON w.id = l.warehouse_id
            GROUP BY w.id, w.name, w.address, w.code
            ORDER BY w.name
        """)
        warehouses_data = cur.fetchall()
        
        # Get locations for each warehouse with hierarchical structure
        warehouse_list = []
        for warehouse in warehouses_data:
            warehouse_dict = dict(warehouse)
            
            # Get locations for this warehouse with hierarchical structure and bin counts
            cur.execute("""
                SELECT 
                    l.*,
                    COUNT(b.id) as bin_count,
                    COUNT(CASE WHEN si.on_hand > 0 THEN 1 END) as occupied_bins
                FROM locations l
                LEFT JOIN bins b ON l.id = b.location_id
                LEFT JOIN stock_items si ON b.id = si.bin_id
                WHERE l.warehouse_id = %s 
                GROUP BY l.id, l.full_code, l.warehouse_id
                ORDER BY l.full_code
            """, (warehouse['id'],))
            locations = cur.fetchall()
            
            # Organize locations hierarchically
            hierarchical_locations = {}
            for loc in locations:
                loc_dict = dict(loc)
                # Parse the full_code to extract hierarchical components
                # Expected format: A2F10 (Area2, RackF, Level10)
                full_code = loc_dict['full_code'] if loc_dict['full_code'] else ''
                
                if len(full_code) >= 4 and full_code.startswith('A'):
                    # Extract area number (A2 -> 2)
                    area_number = full_code[1] if len(full_code) > 1 and full_code[1].isdigit() else '1'
                    area_code = f"A{area_number}"
                    
                    # Extract rack letter (A2F10 -> F)
                    rack_letter = full_code[2] if len(full_code) > 2 else 'A'
                    rack_code = f"R{ord(rack_letter) - ord('A') + 1:02d}"
                    
                    # Extract level number (A2F10 -> 10)
                    level_number = full_code[3:] if len(full_code) > 3 else '1'
                    level_code = f"L{level_number}"
                    
                    warehouse_code = 'W1'  # Default warehouse code
                    
                    # Build hierarchical structure
                    if area_code not in hierarchical_locations:
                        hierarchical_locations[area_code] = {
                            'name': f'Area {area_code}',
                            'code': area_code,
                            'racks': {}
                        }
                    
                    if rack_code not in hierarchical_locations[area_code]['racks']:
                        hierarchical_locations[area_code]['racks'][rack_code] = {
                            'name': f'Rack {rack_code}',
                            'code': rack_code,
                            'levels': {}
                        }
                    
                    if level_code not in hierarchical_locations[area_code]['racks'][rack_code]['levels']:
                        hierarchical_locations[area_code]['racks'][rack_code]['levels'][level_code] = {
                            'name': f'Level {level_code}',
                            'code': level_code,
                            'location_id': loc_dict['id'],
                            'full_code': loc_dict['full_code'],
                            'bin_count': loc_dict['bin_count'] or 0,
                            'occupied_bins': loc_dict['occupied_bins'] or 0
                        }
            
            warehouse_dict['hierarchical_locations'] = hierarchical_locations
            warehouse_dict['locations'] = [dict(loc) for loc in locations] if locations else []
            
            warehouse_list.append(warehouse_dict)
        
        cur.close()
        conn.close()
        return render_template('warehouses.html', warehouses=warehouse_list)
    except Exception as e:
        flash(f'Error loading warehouses: {e}', 'error')
        return render_template('warehouses.html', warehouses=[])

@app.route('/suppliers')
@login_required
def suppliers():
    """Suppliers listing"""
    return render_template('suppliers.html')

@app.route('/reports')
@login_required
def reports():
    """Reports and Analytics Dashboard"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get counts
        cur.execute("SELECT COUNT(*) as count FROM products")
        total_products = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM stock_items")
        total_stock_items = cur.fetchone()['count']
        
        cur.execute("SELECT COUNT(*) as count FROM warehouses")
        total_warehouses = cur.fetchone()['count']
        
        # Get stock data with product and bin information for analysis
        cur.execute("""
            SELECT 
                si.*,
                p.name as product_name, 
                p.sku as product_sku,
                p.batch_tracked,
                b.code as bin_code,
                l.full_code,
                w.name as warehouse_name
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            ORDER BY si.created_at DESC
        """)
        stock_data_raw = cur.fetchall()
        
        # Format the stock data
        stock_data = []
        for item in stock_data_raw:
            item_dict = dict(item)
            # Create nested structure for template compatibility
            item_dict['products'] = {
                'name': item_dict.get('product_name', 'Unknown'),
                'sku': item_dict.get('product_sku', 'N/A'),
                'batch_tracked': item_dict.get('batch_tracked', False)
            }
            item_dict['locations'] = {
                'full_code': item_dict.get('full_code', ''),
                'bin_code': item_dict.get('bin_code', ''),
                'warehouses': {
                    'name': item_dict.get('warehouse_name', 'Unknown')
                }
            }
            stock_data.append(item_dict)
        
        cur.close()
        conn.close()
        
        # Stock distribution analysis
        in_stock_count = 0
        low_stock_count = 0
        out_of_stock_count = 0
        total_inventory_value = 0
        
        # Alerts
        low_stock_alerts = []
        expiry_alerts = []
        
        # Warehouse distribution
        warehouse_distribution = []
        warehouse_stats = {}
        
        if stock_data:
            from datetime import datetime, timedelta
            today = datetime.now().date()
            
            for item in stock_data:
                qty = item.get('on_hand', 0)
                
                # Stock level categorization
                if qty == 0:
                    out_of_stock_count += 1
                elif qty < 10:  # Low stock threshold
                    low_stock_count += 1
                    # Add to alerts
                    if item.get('products'):
                        warehouse_name = 'Unknown'
                        location = 'Unknown'
                        if item.get('locations') and item['locations'].get('warehouses'):
                            warehouse_name = item['locations']['warehouses'].get('name', 'Unknown')
                            location = item['locations'].get('full_code', '')
                        
                        low_stock_alerts.append({
                            'product_name': item['products'].get('name', 'Unknown'),
                            'sku': item['products'].get('sku', 'N/A'),
                            'location': f"{warehouse_name} - {location}",
                            'on_hand': qty
                        })
                else:
                    in_stock_count += 1
                
                # Inventory value (placeholder calculation)
                total_inventory_value += qty * 10.0  # Assume $10 per unit
                
                # Warehouse distribution
                warehouse_name = 'Unknown Warehouse'
                if item.get('locations') and item['locations'].get('warehouses'):
                    warehouse_name = item['locations']['warehouses'].get('name', 'Unknown')
                
                if warehouse_name not in warehouse_stats:
                    warehouse_stats[warehouse_name] = {'total_items': 0, 'total_qty': 0}
                warehouse_stats[warehouse_name]['total_items'] += 1
                warehouse_stats[warehouse_name]['total_qty'] += qty
                
                # Expiry alerts for batch-tracked items
                if item.get('batch_id') and item.get('expiry_date'):
                    try:
                        expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                        days_to_expiry = (expiry_date - today).days
                        
                        if days_to_expiry <= 30:  # Alert for items expiring within 30 days
                            warehouse_name = 'Unknown'
                            location = 'Unknown'
                            if item.get('locations') and item['locations'].get('warehouses'):
                                warehouse_name = item['locations']['warehouses'].get('name', 'Unknown')
                                location = item['locations'].get('full_code', '')
                            
                            expiry_alerts.append({
                                'product_name': item['products'].get('name', 'Unknown') if item.get('products') else 'Unknown',
                                'batch_id': item['batch_id'],
                                'location': f"{warehouse_name} - {location}",
                                'expiry_date': item['expiry_date'],
                                'days_to_expiry': days_to_expiry
                            })
                    except (ValueError, TypeError):
                        pass  # Invalid date format
        
        # Convert warehouse stats to list
        for name, stats in warehouse_stats.items():
            warehouse_distribution.append({
                'name': name,
                'total_items': stats['total_items'],
                'total_qty': stats['total_qty']
            })
        
        # Sort alerts by priority
        low_stock_alerts.sort(key=lambda x: x['on_hand'])
        expiry_alerts.sort(key=lambda x: x['days_to_expiry'])
        
        # Batch analytics (if batch tracking is used)
        batch_analytics = None
        batch_tracked_items = [item for item in (stock_data or []) if item.get('batch_id')]
        if batch_tracked_items:
            batch_analytics = analyze_batch_data(batch_tracked_items)
        
        # Detailed stock report
        detailed_stock_report = []
        for item in (stock_data or []):
            qty_available = item.get('on_hand', 0)
            
            # Determine status
            if qty_available == 0:
                status = 'out_of_stock'
            elif qty_available < 10:
                status = 'low_stock'
            else:
                status = 'in_stock'
            
            # Check if expiring soon
            is_expiring_soon = False
            if item.get('expiry_date'):
                try:
                    expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                    days_to_expiry = (expiry_date - today).days
                    is_expiring_soon = days_to_expiry <= 30
                except (ValueError, TypeError):
                    pass
            
            detailed_stock_report.append({
                'stock_id': item.get('id'),
                'product_name': item['products'].get('name', 'Unknown') if item.get('products') else 'Unknown',
                'sku': item['products'].get('sku', 'N/A') if item.get('products') else 'N/A',
                'warehouse_name': item['locations']['warehouses'].get('name', 'Unknown') if item.get('locations') and item['locations'].get('warehouses') else 'Unknown',
                'location': f"{item['locations'].get('aisle', '')}{item['locations'].get('bin', '')}" if item.get('locations') else 'Unknown',
                'on_hand': qty_available,
                'qty_reserved': item.get('qty_reserved', 0),
                'batch_id': item.get('batch_id'),
                'expiry_date': item.get('expiry_date'),
                'status': status,
                'is_batch_tracked': bool(item.get('batch_id')),
                'is_expiring_soon': is_expiring_soon
            })
        
        return render_template('reports.html',
                             total_products=total_products,
                             total_stock_items=total_stock_items,
                             low_stock_items=low_stock_count,
                             total_inventory_value=total_inventory_value,
                             stock_distribution={
                                 'in_stock': in_stock_count,
                                 'low_stock': low_stock_count,
                                 'out_of_stock': out_of_stock_count
                             },
                             warehouse_distribution=warehouse_distribution,
                             low_stock_alerts=low_stock_alerts,
                             expiry_alerts=expiry_alerts,
                             batch_analytics=batch_analytics,
                             detailed_stock_report=detailed_stock_report)
    
    except Exception as e:
        flash(f'Error loading reports: {e}', 'error')
        return render_template('reports.html',
                             total_products=0,
                             total_stock_items=0,
                             low_stock_items=0,
                             total_inventory_value=0,
                             stock_distribution={'in_stock': 0, 'low_stock': 0, 'out_of_stock': 0},
                             warehouse_distribution=[],
                             low_stock_alerts=[],
                             expiry_alerts=[],
                             batch_analytics=None,
                             detailed_stock_report=[])

def analyze_batch_data(batch_items):
    """Analyze batch tracking data for insights"""
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    total_batches = len(set(item['batch_id'] for item in batch_items if item.get('batch_id')))
    expiring_soon = 0
    expired = 0
    no_expiry = 0
    
    # Expiry timeline for chart (next 12 months)
    expiry_timeline = []
    for i in range(12):
        month_start = today + timedelta(days=30*i)
        month_end = today + timedelta(days=30*(i+1))
        month_name = month_start.strftime('%b %Y')
        
        count = 0
        for item in batch_items:
            if item.get('expiry_date'):
                try:
                    expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                    if month_start <= expiry_date < month_end:
                        count += 1
                except (ValueError, TypeError):
                    pass
        
        expiry_timeline.append({'month': month_name, 'count': count})
    
    # Count categories
    for item in batch_items:
        if not item.get('expiry_date'):
            no_expiry += 1
        else:
            try:
                expiry_date = datetime.strptime(item['expiry_date'], '%Y-%m-%d').date()
                days_to_expiry = (expiry_date - today).days
                
                if days_to_expiry < 0:
                    expired += 1
                elif days_to_expiry <= 30:
                    expiring_soon += 1
            except (ValueError, TypeError):
                no_expiry += 1
    
    return {
        'total_batches': total_batches,
        'expiring_soon': expiring_soon,
        'expired': expired,
        'no_expiry': no_expiry,
        'expiry_timeline': expiry_timeline
    }

# API endpoints for external integration
@app.route('/api/products', methods=['GET'])
def api_products():
    """API endpoint for products"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check for barcode parameter
        barcode = request.args.get('barcode')
        if barcode:
            # Handle PostgREST syntax (eq.) or direct barcode
            if barcode.startswith('eq.'):
                barcode = barcode[3:]  # Remove 'eq.' prefix
            cur.execute("SELECT * FROM products WHERE barcode = %s", (barcode,))
        else:
            cur.execute("SELECT * FROM products ORDER BY created_at DESC")
        
        products_data = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to list of dicts
        products_list = [dict(row) for row in products_data] if products_data else []
        return jsonify(products_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/product/details', methods=['GET'])
@login_required
def product_details_modal():
    """Serve product details modal template"""
    print(f"Modal template request from user {current_user.username if current_user.is_authenticated else 'Not authenticated'}")
    return render_template('product_details_modal.html')

@app.route('/api/product/<product_id>/details', methods=['GET'])
@login_required
def api_product_details(product_id):
    """API endpoint for comprehensive product details"""
    print(f"API request for product {product_id} from user {current_user.username if current_user.is_authenticated else 'Not authenticated'}")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get basic product information with replenishment policies
        cur.execute("""
            SELECT 
                p.*,
                rp.forecasting_mode,
                rp.manual_reorder_point,
                rp.manual_safety_stock,
                rp.manual_lead_time_days,
                rp.forecasting_notes
            FROM products p
            LEFT JOIN replenishment_policies rp ON p.id = rp.product_id
            WHERE p.id = %s
        """, (product_id,))
        product = cur.fetchone()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Get bin-specific stock details
        cur.execute("""
            SELECT 
                si.id,
                si.on_hand,
                si.qty_reserved,
                si.batch_id,
                si.expiry_date,
                si.created_at,
                b.code as bin_code,
                l.full_code,
                w.name as warehouse_name,
                w.address as warehouse_address
            FROM stock_items si
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            WHERE si.product_id = %s
            ORDER BY w.name, l.full_code
        """, (product_id,))
        stock_locations = cur.fetchall()
        
        # Get stock transaction history (last 30 days)
        cur.execute("""
            SELECT 
                st.transaction_type,
                st.quantity_change,
                st.quantity_before,
                st.quantity_after,
                st.created_at,
                st.notes,
                u.username as user_name
            FROM stock_transactions st
            LEFT JOIN stock_items si ON st.stock_item_id = si.id
            LEFT JOIN users u ON st.user_id = u.id
            WHERE si.product_id = %s
            ORDER BY st.created_at DESC
            LIMIT 100
        """, (product_id,))
        transaction_history = cur.fetchall()
        
        # Get stock movement trends (daily for last 30 days)
        cur.execute("""
            SELECT 
                DATE(st.created_at) as date,
                SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as received,
                SUM(CASE WHEN st.transaction_type = 'ship' THEN st.quantity_change ELSE 0 END) as shipped,
                SUM(CASE WHEN st.transaction_type = 'adjust' THEN st.quantity_change ELSE 0 END) as adjusted
            FROM stock_transactions st
            LEFT JOIN stock_items si ON st.stock_item_id = si.id
            WHERE si.product_id = %s 
            AND st.created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(st.created_at)
            ORDER BY date
        """, (product_id,))
        stock_trends = cur.fetchall()
        
        # Calculate forecasting data
        # Get average daily usage (last 30 days)
        cur.execute("""
            SELECT 
                COALESCE(AVG(daily_usage), 0) as avg_daily_usage,
                COALESCE(STDDEV(daily_usage), 0) as usage_std_dev,
                COALESCE(MAX(daily_usage), 0) as max_daily_usage
            FROM (
                SELECT 
                    DATE(st.created_at) as date,
                    ABS(SUM(CASE WHEN st.transaction_type = 'ship' THEN st.quantity_change ELSE 0 END)) as daily_usage
                FROM stock_transactions st
                LEFT JOIN stock_items si ON st.stock_item_id = si.id
                WHERE si.product_id = %s 
                AND st.transaction_type = 'ship'
                AND st.created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(st.created_at)
            ) daily_stats
        """, (product_id,))
        usage_stats = cur.fetchone()
        
        # Calculate reorder point and safety stock using hybrid approach
        avg_daily_usage = usage_stats['avg_daily_usage'] or 0
        usage_std_dev = usage_stats['usage_std_dev'] or 0
        
        # Use the new database function for hybrid forecasting calculation
        cur.execute("""
            SELECT * FROM calculate_product_forecasting(%s, %s, %s)
        """, (product_id, avg_daily_usage, usage_std_dev))
        forecasting_result = cur.fetchone()
        
        if forecasting_result:
            reorder_point = forecasting_result['reorder_point']
            safety_stock = forecasting_result['safety_stock']
            lead_time_days = forecasting_result['lead_time_days']
            calculation_mode = forecasting_result['calculation_mode']
        else:
            # Fallback to original calculation if function fails
            lead_time_days = 7
            safety_stock = max(usage_std_dev * 2, avg_daily_usage * 0.5)
            reorder_point = (avg_daily_usage * lead_time_days) + safety_stock
            calculation_mode = 'automatic'
        
        # Get current total stock
        cur.execute("""
            SELECT 
                COALESCE(SUM(on_hand), 0) as total_available,
                COALESCE(SUM(qty_reserved), 0) as total_reserved,
                COALESCE(SUM(on_hand + qty_reserved), 0) as total_stock
            FROM stock_items 
            WHERE product_id = %s
        """, (product_id,))
        current_stock = cur.fetchone()
        
        # Get warehouse distribution
        cur.execute("""
            SELECT 
                w.name as warehouse_name,
                COUNT(si.id) as locations_count,
                SUM(si.on_hand) as total_available,
                SUM(si.qty_reserved) as total_reserved
            FROM stock_items si
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            WHERE si.product_id = %s
            GROUP BY w.name
            ORDER BY total_available DESC
        """, (product_id,))
        warehouse_distribution = cur.fetchall()
        
        # Get expiry alerts (if batch tracked)
        expiry_alerts = []
        if product['batch_tracked']:
            cur.execute("""
                SELECT 
                    si.batch_id,
                    si.expiry_date,
                    si.on_hand,
                    l.full_code,
                    w.name as warehouse_name
                FROM stock_items si
                LEFT JOIN bins b ON si.bin_id = b.id
                LEFT JOIN locations l ON b.location_id = l.id
                LEFT JOIN warehouses w ON l.warehouse_id = w.id
                WHERE si.product_id = %s 
                AND si.expiry_date IS NOT NULL
                AND si.expiry_date <= CURRENT_DATE + INTERVAL '30 days'
                ORDER BY si.expiry_date
            """, (product_id,))
            expiry_alerts = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Prepare response data
        product_details = {
            'product': dict(product),
            'stock_locations': [dict(loc) for loc in stock_locations],
            'transaction_history': [dict(txn) for txn in transaction_history],
            'stock_trends': [dict(trend) for trend in stock_trends],
            'forecasting': {
                'avg_daily_usage': avg_daily_usage,
                'usage_std_dev': usage_std_dev,
                'max_daily_usage': usage_stats['max_daily_usage'],
                'lead_time_days': lead_time_days,
                'safety_stock': safety_stock,
                'reorder_point': reorder_point,
                'current_stock': current_stock['total_available'],
                'days_of_stock': current_stock['total_available'] / avg_daily_usage if avg_daily_usage > 0 else float('inf'),
                'stock_status': 'low' if current_stock['total_available'] <= reorder_point else 'ok',
                'calculation_mode': calculation_mode
            },
            'warehouse_distribution': [dict(w) for w in warehouse_distribution],
            'expiry_alerts': [dict(alert) for alert in expiry_alerts],
            'summary': {
                'total_locations': len(stock_locations),
                'total_warehouses': len(warehouse_distribution),
                'total_transactions': len(transaction_history),
                'expiring_batches': len(expiry_alerts)
            }
        }
        
        return jsonify(product_details)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/<product_id>/forecasting', methods=['PUT'])
@login_required
def api_update_product_forecasting(product_id):
    """API endpoint to update product forecasting settings"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Validate product exists
        cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
        # Check if replenishment policy exists
        cur.execute("SELECT id FROM replenishment_policies WHERE product_id = %s", (product_id,))
        policy_exists = cur.fetchone()
        
        if policy_exists:
            # Update existing policy
            update_fields = []
            update_values = []
            
            if 'forecasting_mode' in data:
                if data['forecasting_mode'] not in ['automatic', 'manual', 'hybrid']:
                    return jsonify({'error': 'Invalid forecasting mode'}), 400
                update_fields.append('forecasting_mode = %s')
                update_values.append(data['forecasting_mode'])
            
            if 'manual_reorder_point' in data:
                update_fields.append('manual_reorder_point = %s')
                update_values.append(data['manual_reorder_point'])
            
            if 'manual_safety_stock' in data:
                update_fields.append('manual_safety_stock = %s')
                update_values.append(data['manual_safety_stock'])
            
            if 'manual_lead_time_days' in data:
                if data['manual_lead_time_days'] < 1:
                    return jsonify({'error': 'Lead time must be at least 1 day'}), 400
                update_fields.append('manual_lead_time_days = %s')
                update_values.append(data['manual_lead_time_days'])
            
            if 'forecasting_notes' in data:
                update_fields.append('forecasting_notes = %s')
                update_values.append(data['forecasting_notes'])
            
            if update_fields:
                update_fields.append('updated_at = NOW()')
                update_values.append(product_id)
                query = f"""
                    UPDATE replenishment_policies 
                    SET {', '.join(update_fields)}
                    WHERE product_id = %s
                """
                cur.execute(query, update_values)
        else:
            # Create new policy
            cur.execute("""
                INSERT INTO replenishment_policies (
                    product_id, forecasting_mode, manual_reorder_point, 
                    manual_safety_stock, manual_lead_time_days, forecasting_notes
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                product_id,
                data.get('forecasting_mode', 'automatic'),
                data.get('manual_reorder_point'),
                data.get('manual_safety_stock'),
                data.get('manual_lead_time_days', 7),
                data.get('forecasting_notes')
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Forecasting settings updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/barcode/<barcode>', methods=['GET'])
def api_product_by_barcode(barcode):
    """API endpoint to find product by barcode"""
    try:
        products_data = postgrest_request(f'products?barcode=eq.{barcode}&select=*')
        if products_data and len(products_data) > 0:
            return jsonify({
                'found': True,
                'product': products_data[0]
            })
        else:
            return jsonify({
                'found': False,
                'message': f'No product found with barcode: {barcode}'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/<product_id>', methods=['GET'])
def api_stock_by_product(product_id):
    """API endpoint for stock by product"""
    try:
        stock_data = postgrest_request(f'stock_items?product_id=eq.{product_id}&select=*,locations(aisle,bin,warehouses(name))')
        return jsonify(stock_data or [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def api_status():
    """API endpoint for application status"""
    try:
        database_connected = False
        mode = "demo"
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            database_connected = True
            mode = "postgresql"
        except Exception as e:
            print(f"Database connection error: {e}")
            database_connected = False
            mode = "error"
        
        return jsonify({
            'database': database_connected,
            'mode': mode,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/warehouse/<warehouse_id>/occupied-locations', methods=['GET'])
def api_warehouse_occupied_locations(warehouse_id):
    """API endpoint to get occupied locations for a warehouse"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all location IDs that have stock items
        cur.execute("""
            SELECT DISTINCT l.id 
            FROM locations l
            JOIN stock_items si ON l.id = si.location_id
            WHERE l.warehouse_id = %s AND si.qty_available > 0
        """, (warehouse_id,))
        
        occupied_locations = [str(row[0]) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'warehouse_id': warehouse_id,
            'occupied_locations': occupied_locations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SUPPLIER MANAGEMENT API ENDPOINTS
# ============================================================================

@app.route('/api/suppliers', methods=['GET'])
@login_required
def get_suppliers():
    """Get all suppliers"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM suppliers ORDER BY name")
        suppliers = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(s) for s in suppliers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers', methods=['POST'])
@login_required
def create_supplier():
    """Create a new supplier"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO suppliers (name, contact_person, email, phone, address, website, payment_terms)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data['name'],
            data.get('contact_person'),
            data.get('email'),
            data.get('phone'),
            data.get('address'),
            data.get('website'),
            data.get('payment_terms')
        ))
        
        supplier_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Supplier created successfully', 'id': supplier_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers/<supplier_id>', methods=['PUT'])
@login_required
def update_supplier(supplier_id):
    """Update a supplier"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE suppliers 
            SET name = %s, contact_person = %s, email = %s, phone = %s, 
                address = %s, website = %s, payment_terms = %s
            WHERE id = %s
        """, (
            data['name'],
            data.get('contact_person'),
            data.get('email'),
            data.get('phone'),
            data.get('address'),
            data.get('website'),
            data.get('payment_terms'),
            supplier_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Supplier updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/suppliers/<supplier_id>', methods=['DELETE'])
@login_required
def delete_supplier(supplier_id):
    """Delete a supplier"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM suppliers WHERE id = %s", (supplier_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Supplier deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/<product_id>/suppliers', methods=['GET'])
@login_required
def get_product_suppliers(product_id):
    """Get suppliers for a specific product"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT 
                ps.*,
                s.name as supplier_name,
                s.contact_person,
                s.email,
                s.phone
            FROM product_suppliers ps
            JOIN suppliers s ON ps.supplier_id = s.id
            WHERE ps.product_id = %s
            ORDER BY ps.is_preferred DESC, s.name
        """, (product_id,))
        
        suppliers = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify([dict(s) for s in suppliers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/<product_id>/suppliers', methods=['POST'])
@login_required
def add_product_supplier(product_id):
    """Add a supplier to a product"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO product_suppliers (
                product_id, supplier_id, supplier_sku, unit_cost, 
                lead_time_days, minimum_order_quantity, is_preferred
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            product_id,
            data['supplier_id'],
            data.get('supplier_sku'),
            data.get('unit_cost'),
            data.get('lead_time_days'),
            data.get('minimum_order_quantity'),
            data.get('is_preferred', False)
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Supplier added to product successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/product-supplier/<product_supplier_id>', methods=['DELETE'])
@login_required
def remove_product_supplier(product_supplier_id):
    """Remove a supplier from a product"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM product_suppliers WHERE id = %s", (product_supplier_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'Supplier removed from product successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_database_schema():
    """Get complete database schema information"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        schema_data = {}
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table['table_name']
            table_data = {
                'columns': [],
                'foreign_keys': [],
                'primary_keys': [],
                'check_constraints': [],
                'row_count': 0
            }
            
            # Get columns
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            columns = cursor.fetchall()
            
            for col in columns:
                table_data['columns'].append({
                    'name': col['column_name'],
                    'type': col['data_type'],
                    'nullable': col['is_nullable'],
                    'default': col['column_default']
                })
            
            # Get primary keys
            cursor.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass AND i.indisprimary
            """, (table_name,))
            pks = cursor.fetchall()
            table_data['primary_keys'] = [pk['attname'] for pk in pks]
            
            # Get foreign keys
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS references_table,
                    ccu.column_name AS references_column
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                    AND tc.table_schema = 'public'
                    AND tc.table_name = %s
            """, (table_name,))
            fks = cursor.fetchall()
            
            for fk in fks:
                table_data['foreign_keys'].append({
                    'constraint_name': fk['constraint_name'],
                    'column': fk['column_name'],
                    'references_table': fk['references_table'],
                    'references_column': fk['references_column']
                })
            
            # Get check constraints
            cursor.execute("""
                SELECT cc.constraint_name, cc.check_clause
                FROM information_schema.check_constraints cc
                JOIN information_schema.table_constraints tc
                    ON cc.constraint_name = tc.constraint_name
                WHERE tc.table_schema = 'public' AND tc.table_name = %s
            """, (table_name,))
            checks = cursor.fetchall()
            
            for check in checks:
                table_data['check_constraints'].append({
                    'constraint_name': check['constraint_name'],
                    'check_clause': check['check_clause']
                })
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count_result = cursor.fetchone()
                table_data['row_count'] = count_result['count'] if count_result else 0
            except:
                table_data['row_count'] = 0
            
            schema_data[table_name] = table_data
        
        cursor.close()
        conn.close()
        return schema_data
        
    except Exception as e:
        print(f"Error getting schema: {e}")
        return {}

@app.route('/admin/schema')
@login_required
def admin_schema():
    """Admin-only database schema viewer"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    schema_data = get_database_schema()
    return render_template('admin_schema.html', schema_data=schema_data)

# Modal edit routes
@app.route('/edit/product/<product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Edit product via modal"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('products'))
    
    is_modal = request.args.get('modal') == '1'
    
    try:
        if request.method == 'POST':
            # Handle form submission
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                
                # Update product using direct database query
                cur.execute("""
                    UPDATE products 
                    SET sku = %s, name = %s, description = %s, dimensions = %s, 
                        weight = %s, barcode = %s, picture_url = %s, batch_tracked = %s
                    WHERE id = %s
                """, (
                    request.form.get('sku'),
                    request.form.get('name'),
                    request.form.get('description') or None,
                    request.form.get('dimensions') or None,
                    float(request.form.get('weight')) if request.form.get('weight') else None,
                    request.form.get('barcode') or None,
                    request.form.get('picture_url') or None,
                    request.form.get('batch_tracked') == 'on',
                    product_id
                ))
                
                conn.commit()
                cur.close()
                conn.close()
                
                if is_modal:
                    return '<div class="alert alert-success">Product updated successfully!</div>'
                else:
                    flash('Product updated successfully!', 'success')
                    return redirect(url_for('products'))
                    
            except Exception as e:
                error_msg = f'Error updating product: {e}'
                if is_modal:
                    return f'<div class="alert alert-danger">{error_msg}</div>'
                else:
                    flash(error_msg, 'error')
                    return redirect(url_for('products'))
        
        else:
            # GET request - show form
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                
                # Fetch product data using direct database query
                cur.execute("""
                    SELECT id, sku, name, description, dimensions, weight, barcode, picture_url, batch_tracked
                    FROM products 
                    WHERE id = %s
                """, (product_id,))
                
                product_row = cur.fetchone()
                if not product_row:
                    flash('Product not found.', 'error')
                    return redirect(url_for('products'))
            
                # Convert to dictionary format
                product = {
                    'id': product_row[0],
                    'sku': product_row[1],
                    'name': product_row[2],
                    'description': product_row[3],
                    'dimensions': product_row[4],
                    'weight': product_row[5],
                    'barcode': product_row[6],
                    'picture_url': product_row[7],
                    'batch_tracked': product_row[8]
                }
                
                cur.close()
                conn.close()
                
                if is_modal:
                    return render_template('edit_product_modal.html', product=product)
                else:
                    return render_template('edit_product.html', product=product)
                    
            except Exception as e:
                flash(f'Error loading product: {e}', 'error')
                return redirect(url_for('products'))
                
    except Exception as e:
        error_msg = f'Error updating product: {e}'
        if is_modal:
            return f'<div class="alert alert-danger">{error_msg}</div>'
        else:
            flash(error_msg, 'error')
            return redirect(url_for('products'))

@app.route('/edit/stock/<stock_id>', methods=['GET', 'POST'])
@login_required
def edit_stock(stock_id):
    """Edit stock item via modal"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('stock'))
    
    is_modal = request.args.get('modal') == '1'
    
    try:
        if request.method == 'POST':
            # Handle form submission
            data = {
                'product_id': request.form.get('product_id'),
                'location_id': request.form.get('location_id'),
                'on_hand': int(request.form.get('qty_available')),
                'qty_reserved': int(request.form.get('qty_reserved'))
            }
            
            # Update via PostgREST
            response = postgrest_request(f'stock_items?id=eq.{stock_id}', 'PATCH', data)
            
            if is_modal:
                return '<div class="alert alert-success">Stock updated successfully!</div>'
            else:
                flash('Stock updated successfully!', 'success')
                return redirect(url_for('stock'))
        
        else:
            # GET request - show form
            stock_data = postgrest_request(f'stock_items?id=eq.{stock_id}&select=*')
            products_data = postgrest_request('products?select=id,sku,name')
            locations_data = postgrest_request('locations?select=id,aisle,bin,warehouses(name)')
            
            if not stock_data:
                flash('Stock item not found.', 'error')
                return redirect(url_for('stock'))
            
            stock = stock_data[0]
            # Format locations for dropdown
            formatted_locations = []
            for loc in locations_data or []:
                warehouse_name = loc.get('warehouses', {}).get('name', 'Unknown') if loc.get('warehouses') else 'Unknown'
                formatted_locations.append({
                    'id': loc['id'],
                    'aisle': loc['aisle'],
                    'bin': loc['bin'],
                    'warehouse_name': warehouse_name
                })
            
            if is_modal:
                return render_template('edit_stock_modal.html', 
                                     stock=stock, 
                                     products=products_data or [], 
                                     locations=formatted_locations)
            else:
                return render_template('edit_stock.html', 
                                     stock=stock, 
                                     products=products_data or [], 
                                     locations=formatted_locations)
                
    except Exception as e:
        error_msg = f'Error updating stock: {e}'
        if is_modal:
            return f'<div class="alert alert-danger">{error_msg}</div>'
        else:
            flash(error_msg, 'error')
            return redirect(url_for('stock'))

@app.route('/edit/warehouse/<warehouse_id>', methods=['GET', 'POST'])
@login_required
def edit_warehouse(warehouse_id):
    """Edit warehouse via modal"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('warehouses'))
    
    is_modal = request.args.get('modal') == '1'
    
    try:
        if request.method == 'POST':
            # Handle form submission
            name = request.form.get('name')
            address = request.form.get('address') or None
            aisles_data = request.form.get('aisles_data')
            
            # Validate occupied locations before making changes
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get current locations
            cur.execute("SELECT id, aisle, bin FROM locations WHERE warehouse_id = %s", (warehouse_id,))
            current_locations = cur.fetchall()
            current_location_ids = {loc[0] for loc in current_locations}
            
            # Get occupied locations
            cur.execute("""
                SELECT DISTINCT l.id 
                FROM locations l
                JOIN stock_items si ON l.id = si.location_id
                WHERE l.warehouse_id = %s AND si.qty_available > 0
            """, (warehouse_id,))
            occupied_location_ids = {row[0] for row in cur.fetchall()}
            
            # Parse new hierarchical configuration
            hierarchical_data = request.form.get('hierarchical_data')
            if hierarchical_data:
                try:
                    hierarchical_structure = json.loads(hierarchical_data)
                    
                    # Update warehouse name and address
                    cur.execute("UPDATE warehouses SET name = %s, address = %s WHERE id = %s", 
                               (name, address, warehouse_id))
                    
                    # Get current locations to check for occupied ones
                    cur.execute("SELECT id, full_code FROM locations WHERE warehouse_id = %s", (warehouse_id,))
                    current_locations = cur.fetchall()
                    current_location_ids = {loc[0] for loc in current_locations}
                    current_location_codes = {loc[1] for loc in current_locations}
                    
                    # Get occupied locations (locations with bins that have stock)
                    cur.execute("""
                        SELECT DISTINCT l.id 
                        FROM locations l
                        JOIN bins b ON l.id = b.location_id
                        JOIN stock_items si ON b.id = si.bin_id
                        WHERE l.warehouse_id = %s AND si.on_hand > 0
                    """, (warehouse_id,))
                    occupied_location_ids = {row[0] for row in cur.fetchall()}
                    
                    # Calculate new location codes from hierarchical structure
                    new_location_codes = set()
                    for area_code, area in hierarchical_structure.items():
                        for rack_code, rack in area['racks'].items():
                            for level_code, level in rack['levels'].items():
                                # Generate full_code: A2F10 (Area2, RackF, Level10)
                                # Convert rack_code from R01 format to letter (R01->A, R02->B, etc.)
                                rack_letter = chr(ord('A') + int(rack_code.replace('R', '')) - 1) if rack_code.startswith('R') else rack_code
                                # Extract area number from A01 format
                                area_number = area_code.replace('A', '') if area_code.startswith('A') else area_code
                                # Extract level number from L1 format
                                level_number = level_code.replace('L', '') if level_code.startswith('L') else level_code
                                full_code = f"A{area_number}{rack_letter}{level_number}"
                                new_location_codes.add(full_code)
                    
                    # Find locations that will be removed
                    removed_location_codes = current_location_codes - new_location_codes
                    
                    # Check if any removed locations are occupied
                    if removed_location_codes:
                        cur.execute("SELECT id, full_code FROM locations WHERE full_code = ANY(%s)", (list(removed_location_codes),))
                        removed_locations = cur.fetchall()
                        removed_location_ids = {loc[0] for loc in removed_locations}
                        occupied_removed = removed_location_ids & occupied_location_ids
                        
                        if occupied_removed:
                            # Get details of occupied locations
                            cur.execute("""
                                SELECT l.full_code, COUNT(si.id) as stock_count
                                FROM locations l
                                JOIN bins b ON l.id = b.location_id
                                JOIN stock_items si ON b.id = si.bin_id
                                WHERE l.id = ANY(%s) AND si.on_hand > 0
                                GROUP BY l.id, l.full_code
                            """, (list(occupied_removed),))
                            occupied_details = cur.fetchall()
                            
                            error_msg = f"Cannot remove occupied locations. The following locations have stock items: " + \
                                      ", ".join([f"{loc[0]} ({loc[1]} items)" for loc in occupied_details]) + \
                                      ". Please move or remove the stock items first."
                            cur.close()
                            conn.close()
                            
                            if is_modal:
                                return f'<div class="alert alert-danger">{error_msg}</div>'
                            else:
                                flash(error_msg, 'error')
                                return redirect(url_for('warehouses'))
                    
                    # Remove locations that are no longer needed
                    if removed_location_codes:
                        cur.execute("DELETE FROM locations WHERE full_code = ANY(%s)", (list(removed_location_codes),))
                    
                    # Add/update locations based on hierarchical structure
                    for area_code, area in hierarchical_structure.items():
                        for rack_code, rack in area['racks'].items():
                            for level_code, level in rack['levels'].items():
                                # Generate full_code: A2F10 (Area2, RackF, Level10)
                                # Convert rack_code from R01 format to letter (R01->A, R02->B, etc.)
                                rack_letter = chr(ord('A') + int(rack_code.replace('R', '')) - 1) if rack_code.startswith('R') else rack_code
                                # Extract area number from A01 format
                                area_number = area_code.replace('A', '') if area_code.startswith('A') else area_code
                                # Extract level number from L1 format
                                level_number = level_code.replace('L', '') if level_code.startswith('L') else level_code
                                full_code = f"A{area_number}{rack_letter}{level_number}"
                                
                                # Check if location already exists
                                cur.execute("SELECT id FROM locations WHERE full_code = %s AND warehouse_id = %s", 
                                           (full_code, warehouse_id))
                                existing_location = cur.fetchone()
                                
                                if existing_location:
                                    # Update existing location
                                    cur.execute("UPDATE locations SET full_code = %s WHERE id = %s", 
                                               (full_code, existing_location[0]))
                                else:
                                    # Create new location
                                    cur.execute("INSERT INTO locations (warehouse_id, full_code) VALUES (%s, %s) RETURNING id", 
                                               (warehouse_id, full_code))
                    
                    conn.commit()
                    
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    error_msg = f"Error parsing hierarchical data: {e}"
                    cur.close()
                    conn.close()
                    
                    if is_modal:
                        return f'<div class="alert alert-danger">{error_msg}</div>'
                    else:
                        flash(error_msg, 'error')
                        return redirect(url_for('warehouses'))
            else:
                # Just update name and address if no hierarchical data provided
                cur.execute("UPDATE warehouses SET name = %s, address = %s WHERE id = %s", 
                           (name, address, warehouse_id))
                conn.commit()
            
            cur.close()
            conn.close()
            
            if is_modal:
                return '<div class="alert alert-success">Warehouse updated successfully!</div>'
            else:
                flash('Warehouse updated successfully!', 'success')
                return redirect(url_for('warehouses'))
        
        else:
            # GET request - show form
            # Use direct database query instead of PostgREST for reliability
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get warehouse data
            cur.execute("SELECT * FROM warehouses WHERE id = %s", (warehouse_id,))
            warehouse_data = cur.fetchone()
            
            if not warehouse_data:
                cur.close()
                conn.close()
                flash('Warehouse not found.', 'error')
                return redirect(url_for('warehouses'))
            
            warehouse = dict(warehouse_data)
            
            # Get locations for this warehouse
            cur.execute("SELECT * FROM locations WHERE warehouse_id = %s ORDER BY aisle, bin", (warehouse_id,))
            locations = cur.fetchall()
            warehouse['locations'] = [dict(loc) for loc in locations] if locations else []
            
            cur.close()
            conn.close()
            
            if is_modal:
                return render_template('edit_warehouse_modal.html', warehouse=warehouse)
            else:
                return render_template('edit_warehouse.html', warehouse=warehouse)
                
    except Exception as e:
        error_msg = f'Error updating warehouse: {e}'
        if is_modal:
            return f'<div class="alert alert-danger">{error_msg}</div>'
        else:
            flash(error_msg, 'error')
            return redirect(url_for('warehouses'))

# Delete routes
@app.route('/delete/product/<product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete product"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('products'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Delete the product
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        
        if cur.rowcount == 0:
            flash('Product not found.', 'error')
        else:
            conn.commit()
        flash('Product deleted successfully!', 'success')
        
        cur.close()
        conn.close()
    except Exception as e:
        flash(f'Error deleting product: {e}', 'error')
    
    return redirect(url_for('products'))

@app.route('/delete/stock/<stock_id>', methods=['POST'])
@login_required
def delete_stock(stock_id):
    """Delete stock item"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('stock'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Delete the stock item
        cur.execute("DELETE FROM stock_items WHERE id = %s", (stock_id,))
        
        if cur.rowcount == 0:
            flash('Stock item not found.', 'error')
        else:
            conn.commit()
        flash('Stock item deleted successfully!', 'success')
        
        cur.close()
        conn.close()
    except Exception as e:
        flash(f'Error deleting stock item: {e}', 'error')
    
    return redirect(url_for('stock'))

@app.route('/delete/warehouse/<warehouse_id>', methods=['POST'])
@login_required
def delete_warehouse(warehouse_id):
    """Delete warehouse with new logic:
    1. Collect all descendant locations of the warehouse
    2. Find all bins currently assigned to those locations
    3. Check if those bins contain stock:
       - If yes → abort with a warning (warehouse not empty)
       - If no → Delete the locations and set bin.location_id = NULL (bins become "floating")
    """
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('warehouses'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Step 1: Collect all descendant locations of the warehouse
        cur.execute("""
            SELECT id, full_code FROM locations 
            WHERE warehouse_id = %s
        """, (warehouse_id,))
        warehouse_locations = cur.fetchall()
        
        if not warehouse_locations:
            # No locations found, just delete the warehouse
            cur.execute("DELETE FROM warehouses WHERE id = %s", (warehouse_id,))
            if cur.rowcount == 0:
                flash('Warehouse not found.', 'error')
            else:
                conn.commit()
                flash('Warehouse deleted successfully!', 'success')
            cur.close()
            conn.close()
            return redirect(url_for('warehouses'))
        
        location_ids = [loc[0] for loc in warehouse_locations]
        
        # Step 2: Find all bins currently assigned to those locations
        cur.execute("""
            SELECT b.id, b.code, l.full_code 
            FROM bins b
            JOIN locations l ON b.location_id = l.id
            WHERE b.location_id = ANY(%s::uuid[])
        """, (location_ids,))
        assigned_bins = cur.fetchall()
        
        # Step 3: Check if those bins contain stock
        if assigned_bins:
            bin_ids = [bin[0] for bin in assigned_bins]
            cur.execute("""
                SELECT COUNT(*) FROM stock_items 
                WHERE bin_id = ANY(%s::uuid[]) AND on_hand > 0
            """, (bin_ids,))
            stock_count = cur.fetchone()[0]
            
            if stock_count > 0:
                # Get detailed information about occupied bins for better error message
                cur.execute("""
                    SELECT b.code, l.full_code, si.on_hand, p.name
                    FROM stock_items si
                    JOIN bins b ON si.bin_id = b.id
                    JOIN locations l ON b.location_id = l.id
                    JOIN products p ON si.product_id = p.id
                    WHERE si.bin_id = ANY(%s::uuid[]) AND si.on_hand > 0
                    ORDER BY l.full_code, b.code
                """, (bin_ids,))
                occupied_bins_details = cur.fetchall()
                
                # Build detailed error message
                error_msg = f"Cannot delete warehouse: {stock_count} stock items are still located in this warehouse.\n\nOccupied locations:\n"
                for bin_code, location_code, qty, product_name in occupied_bins_details:
                    error_msg += f"• Location {location_code}, Bin {bin_code}: {qty} units of {product_name}\n"
                
                flash(error_msg, 'error')
                cur.close()
                conn.close()
                return redirect(url_for('warehouses'))
        
        # Step 4: If no stock found, proceed with deletion
        # First, set all bins to "floating" (location_id = NULL)
        if assigned_bins:
            cur.execute("""
                UPDATE bins 
                SET location_id = NULL 
                WHERE location_id = ANY(%s::uuid[])
            """, (location_ids,))
            bins_updated = cur.rowcount
        
        # Delete all locations
        cur.execute("DELETE FROM locations WHERE warehouse_id = %s", (warehouse_id,))
        locations_deleted = cur.rowcount
        
        # Delete the warehouse
        cur.execute("DELETE FROM warehouses WHERE id = %s", (warehouse_id,))
        warehouse_deleted = cur.rowcount
        
        if warehouse_deleted == 0:
            flash('Warehouse not found.', 'error')
        else:
            conn.commit()
            success_msg = f"Warehouse deleted successfully!"
            if bins_updated > 0:
                success_msg += f" {bins_updated} bin(s) are now floating and available for reassignment."
            flash(success_msg, 'success')
        
        cur.close()
        conn.close()
    except Exception as e:
        flash(f'Error deleting warehouse: {e}', 'error')
    
    return redirect(url_for('warehouses'))

# Add/Create routes
@app.route('/add/product', methods=['GET', 'POST'])
@login_required
def add_product():
    """Add new product via modal"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('products'))
    
    is_modal = request.args.get('modal') == '1'
    
    try:
        if request.method == 'POST':
            # Handle form submission
            data = {
                'sku': request.form.get('sku'),
                'name': request.form.get('name'),
                'description': request.form.get('description') or None,
                'dimensions': request.form.get('dimensions') or None,
                'weight': float(request.form.get('weight')) if request.form.get('weight') else None,
                'barcode': request.form.get('barcode') or None,
                'picture_url': request.form.get('picture_url') or None,
                'batch_tracked': request.form.get('batch_tracked') == 'on'
            }
            
            # Create via PostgREST
            response = postgrest_request('products', 'POST', data)
            
            if is_modal:
                return '<div class="alert alert-success">Product created successfully!</div>'
            else:
                flash('Product created successfully!', 'success')
                return redirect(url_for('products'))
        
        else:
            # GET request - show form
            if is_modal:
                return render_template('add_product_modal.html')
            else:
                return render_template('add_product.html')
                
    except Exception as e:
        error_msg = f'Error creating product: {e}'
        if is_modal:
            return f'<div class="alert alert-danger">{error_msg}</div>'
        else:
            flash(error_msg, 'error')
            return redirect(url_for('products'))

@app.route('/add/stock', methods=['GET', 'POST'])
@login_required
def add_stock():
    """Add new stock item via modal"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('stock'))
    
    is_modal = request.args.get('modal') == '1'
    
    try:
        if request.method == 'POST':
            # Handle form submission using smart stock receiving logic
            product_id = request.form.get('product_id')
            location_id = request.form.get('location_id')
            qty_available = int(request.form.get('qty_available'))
            qty_reserved = int(request.form.get('qty_reserved', 0))
            batch_id = request.form.get('batch_id') or None
            expiry_date = request.form.get('expiry_date') or None
            
            # Use smart stock receiving function
            response = handle_stock_receiving(
                product_id, location_id, qty_available, qty_reserved, batch_id, expiry_date
            )
            
            if is_modal:
                return '<div class="alert alert-success">Stock item created successfully!</div>'
            else:
                flash('Stock item created successfully!', 'success')
                return redirect(url_for('stock'))
        
        else:
            # GET request - show form
            products_data = postgrest_request('products?select=id,sku,name')
            locations_data = postgrest_request('locations?select=id,aisle,bin,warehouses(name)')
            
            # Format locations for dropdown
            formatted_locations = []
            for loc in locations_data or []:
                warehouse_name = loc.get('warehouses', {}).get('name', 'Unknown') if loc.get('warehouses') else 'Unknown'
                formatted_locations.append({
                    'id': loc['id'],
                    'aisle': loc['aisle'],
                    'bin': loc['bin'],
                    'warehouse_name': warehouse_name
                })
            
            if is_modal:
                return render_template('add_stock_modal.html', 
                                     products=products_data or [], 
                                     locations=formatted_locations)
            else:
                return render_template('add_stock.html', 
                                     products=products_data or [], 
                                     locations=formatted_locations)
                
    except Exception as e:
        error_msg = f'Error creating stock item: {e}'
        if is_modal:
            return f'<div class="alert alert-danger">{error_msg}</div>'
        else:
            flash(error_msg, 'error')
            return redirect(url_for('stock'))

@app.route('/add/warehouse', methods=['GET', 'POST'])
@login_required
def add_warehouse():
    """Add new warehouse via modal"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('warehouses'))
    
    is_modal = request.args.get('modal') == '1'
    
    try:
        if request.method == 'POST':
            # Handle form submission
            warehouse_data = {
                'name': request.form.get('name'),
                'address': request.form.get('address') or None
            }
            
            # Create warehouse via direct database query
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("INSERT INTO warehouses (name, address) VALUES (%s, %s) RETURNING id", 
                       (warehouse_data['name'], warehouse_data['address']))
            warehouse_id = cur.fetchone()[0]
            
            # Create locations based on the new hierarchical data format
            hierarchical_data = request.form.get('hierarchical_data')
            if hierarchical_data:
                try:
                    hierarchical_structure = json.loads(hierarchical_data)
                    
                    # Create locations based on hierarchical structure
                    for area_code, area in hierarchical_structure.items():
                        for rack_code, rack in area['racks'].items():
                            for level_code, level in rack['levels'].items():
                                # Generate full_code: A2F10 (Area2, RackF, Level10)
                                # Convert rack_code from R01 format to letter (R01->A, R02->B, etc.)
                                rack_letter = chr(ord('A') + int(rack_code.replace('R', '')) - 1) if rack_code.startswith('R') else rack_code
                                # Extract area number from A01 format
                                area_number = area_code.replace('A', '') if area_code.startswith('A') else area_code
                                # Extract level number from L1 format
                                level_number = level_code.replace('L', '') if level_code.startswith('L') else level_code
                                full_code = f"A{area_number}{rack_letter}{level_number}"
                                cur.execute("INSERT INTO locations (warehouse_id, full_code) VALUES (%s, %s)", 
                                           (warehouse_id, full_code))
                    
                    conn.commit()
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"Error parsing hierarchical data: {e}")
                    # Fallback to simple structure if hierarchical format fails
                    cur.execute("INSERT INTO locations (warehouse_id, full_code) VALUES (%s, %s)", 
                               (warehouse_id, 'A1A1'))
                    conn.commit()
            
            cur.close()
            conn.close()
            
            if is_modal:
                return '<div class="alert alert-success">Warehouse created successfully!</div>'
            else:
                flash('Warehouse created successfully!', 'success')
                return redirect(url_for('warehouses'))
        
        else:
            # GET request - show form
            if is_modal:
                return render_template('add_warehouse_modal.html')
            else:
                return render_template('add_warehouse.html')
                
    except Exception as e:
        error_msg = f'Error creating warehouse: {e}'
        if is_modal:
            return f'<div class="alert alert-danger">{error_msg}</div>'
        else:
            flash(error_msg, 'error')
            return redirect(url_for('warehouses'))

@app.route('/transactions')
@login_required
def transactions():
    """Stock transactions page"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get transactions with related data
        cur.execute("""
            SELECT 
                st.id,
                st.transaction_type,
                st.quantity_change,
                st.quantity_before,
                st.quantity_after,
                st.notes,
                st.created_at,
                st.reference_id,
                p.sku,
                p.name as product_name,
                b.code as bin_code,
                w.name as warehouse_name,
                l.full_code,
                u.username as user_name
            FROM stock_transactions st
            LEFT JOIN stock_items si ON st.stock_item_id = si.id
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            LEFT JOIN users u ON st.user_id = u.id
            ORDER BY st.created_at DESC
        """)
        
        transactions = cur.fetchall()
        
        # Get summary statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(DISTINCT st.stock_item_id) as unique_stock_items,
                COUNT(DISTINCT p.id) as unique_products,
                SUM(CASE WHEN st.transaction_type = 'receive' THEN st.quantity_change ELSE 0 END) as total_received,
                SUM(CASE WHEN st.transaction_type = 'ship' THEN ABS(st.quantity_change) ELSE 0 END) as total_shipped,
                SUM(CASE WHEN st.transaction_type = 'adjust' THEN st.quantity_change ELSE 0 END) as total_adjusted
            FROM stock_transactions st
            LEFT JOIN stock_items si ON st.stock_item_id = si.id
            LEFT JOIN products p ON si.product_id = p.id
        """)
        
        stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return render_template('transactions.html', 
                             transactions=transactions, 
                             stats=stats)
                             
    except Exception as e:
        print(f"Error loading transactions: {e}")
        flash('Error loading transactions', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/transactions', methods=['GET'])
@login_required
def api_transactions():
    """Get transactions with filtering and pagination"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        transaction_type = request.args.get('type', '')
        product_id = request.args.get('product_id', '')
        warehouse_id = request.args.get('warehouse_id', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Build WHERE clause
        where_conditions = []
        params = []
        
        if transaction_type:
            where_conditions.append("st.transaction_type = %s")
            params.append(transaction_type)
        
        if product_id:
            where_conditions.append("p.id = %s")
            params.append(product_id)
        
        if warehouse_id:
            where_conditions.append("w.id = %s")
            params.append(warehouse_id)
        
        if date_from:
            where_conditions.append("st.created_at >= %s")
            params.append(date_from)
        
        if date_to:
            where_conditions.append("st.created_at <= %s")
            params.append(date_to)
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*)
            FROM stock_transactions st
            LEFT JOIN stock_items si ON st.stock_item_id = si.id
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            {where_clause}
        """
        cur.execute(count_query, params)
        total_count = cur.fetchone()['count']
        
        # Get paginated results
        offset = (page - 1) * per_page
        query = f"""
            SELECT 
                st.id,
                st.transaction_type,
                st.quantity_change,
                st.quantity_before,
                st.quantity_after,
                st.notes,
                st.created_at,
                st.reference_id,
                p.sku,
                p.name as product_name,
                p.id as product_id,
                b.code as bin_code,
                w.name as warehouse_name,
                w.id as warehouse_id,
                l.full_code,
                u.username as user_name
            FROM stock_transactions st
            LEFT JOIN stock_items si ON st.stock_item_id = si.id
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            LEFT JOIN users u ON st.user_id = u.id
            {where_clause}
            ORDER BY st.created_at DESC
            LIMIT %s OFFSET %s
        """
        cur.execute(query, params + [per_page, offset])
        transactions = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'transactions': [dict(t) for t in transactions],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500

@app.route('/api/transactions/<transaction_id>', methods=['GET'])
@login_required
def api_transaction_detail(transaction_id):
    """Get detailed information about a specific transaction"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT 
                st.*,
                p.sku,
                p.name as product_name,
                p.description as product_description,
                b.code as bin_code,
                w.name as warehouse_name,
                l.full_code,
                u.username as user_name,
                u.role as user_role
            FROM stock_transactions st
            LEFT JOIN stock_items si ON st.stock_item_id = si.id
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            LEFT JOIN users u ON st.user_id = u.id
            WHERE st.id = %s
        """, (transaction_id,))
        
        transaction = cur.fetchone()
        cur.close()
        conn.close()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        return jsonify(dict(transaction))
        
    except Exception as e:
        print(f"Error fetching transaction detail: {e}")
        return jsonify({'error': 'Failed to fetch transaction detail'}), 500

@app.route('/api/transactions', methods=['POST'])
@login_required
def api_create_transaction():
    """Create a new stock transaction"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['stock_item_id', 'transaction_type', 'quantity_change', 'notes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate transaction type
        valid_types = ['receive', 'ship', 'adjust', 'transfer', 'reserve', 'release']
        if data['transaction_type'] not in valid_types:
            return jsonify({'error': f'Invalid transaction type. Must be one of: {", ".join(valid_types)}'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get current stock levels
        cur.execute("""
            SELECT on_hand, qty_reserved 
            FROM stock_items 
            WHERE id = %s
        """, (data['stock_item_id'],))
        
        stock_item = cur.fetchone()
        if not stock_item:
            cur.close()
            conn.close()
            return jsonify({'error': 'Stock item not found'}), 404
        
        quantity_before = stock_item['on_hand']
        quantity_after = quantity_before + data['quantity_change']
        
        # Validate stock levels for outgoing transactions
        if data['transaction_type'] in ['ship', 'transfer'] and quantity_after < 0:
            cur.close()
            conn.close()
            return jsonify({'error': 'Insufficient stock for this transaction'}), 400
        
        # Update stock levels
        cur.execute("""
            UPDATE stock_items 
            SET on_hand = %s 
            WHERE id = %s
        """, (quantity_after, data['stock_item_id']))
        
        # Create transaction record
        cur.execute("""
            INSERT INTO stock_transactions 
            (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id, reference_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data['stock_item_id'],
            data['transaction_type'],
            data['quantity_change'],
            quantity_before,
            quantity_after,
            data['notes'],
            current_user.id,
            data.get('reference_id')
        ))
        
        transaction_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'message': 'Transaction created successfully',
            'transaction_id': transaction_id,
            'quantity_before': quantity_before,
            'quantity_after': quantity_after
        }), 201
        
    except Exception as e:
        print(f"Error creating transaction: {e}")
        return jsonify({'error': 'Failed to create transaction'}), 500

@app.route('/api/stock-items', methods=['GET'])
@login_required
def api_stock_items():
    """Get stock items for transaction form"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT 
                si.id,
                si.on_hand,
                si.qty_reserved,
                p.sku,
                p.name as product_name,
                b.code as bin_code,
                w.name as warehouse_name,
                l.full_code
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            ORDER BY p.name, w.name, l.full_code
        """)
        
        stock_items = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify({
            'stock_items': [dict(item) for item in stock_items]
        })
        
    except Exception as e:
        print(f"Error fetching stock items: {e}")
        return jsonify({'error': 'Failed to fetch stock items'}), 500

@app.route('/api/warehouses', methods=['GET'])
@login_required
def api_warehouses():
    """Get warehouses for filter dropdown"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT id, name, address
            FROM warehouses
            ORDER BY name
        """)
        
        warehouses = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify({
            'warehouses': [dict(warehouse) for warehouse in warehouses]
        })
        
    except Exception as e:
        print(f"Error fetching warehouses: {e}")
        return jsonify({'error': 'Failed to fetch warehouses'}), 500

@app.route('/scanner')
@login_required
def scanner():
    """Barcode scanner interface for warehouse operations"""
    return render_template('scanner.html')

@app.route('/api/location/<location_code>', methods=['GET'])
@login_required
def api_location_details(location_code):
    """API endpoint to get location details and associated stock items"""
    try:
        # Parse hierarchical location code (e.g., W1-A01-R01-L1-B01)
        if not location_code or '-' not in location_code:
            return jsonify({'error': 'Invalid location code format. Expected format: W1-A01-R01-L1-B01'}), 400
        
        # Get location details and associated stock items
        cur = get_db_connection().cursor()
        
        # Find the location using the new hierarchical structure
        cur.execute("""
            SELECT l.id, l.full_code, l.warehouse_code, l.area_code, l.rack_code, l.level_number, l.bin_number,
                   l.warehouse_id, w.name as warehouse_name, w.address as warehouse_address
            FROM locations l
            JOIN warehouses w ON l.warehouse_id = w.id
            WHERE l.full_code = %s
        """, (location_code,))
        
        location_result = cur.fetchone()
        if not location_result:
            return jsonify({'error': f'Location {location_code} not found'}), 404
        
        location_id, full_code, warehouse_code, area_code, rack_code, level_number, bin_number, warehouse_id, warehouse_name, warehouse_address = location_result
        
        # Get stock items at this location (via bins)
        cur.execute("""
            SELECT 
                si.id,
                si.on_hand,
                si.qty_reserved,
                si.batch_id,
                si.expiry_date,
                p.id as product_id,
                p.name as product_name,
                p.sku,
                p.barcode,
                p.description,
                p.batch_tracked,
                b.code as bin_code
            FROM stock_items si
            JOIN products p ON si.product_id = p.id
            JOIN bins b ON si.bin_id = b.id
            WHERE b.location_id = %s
            ORDER BY p.name
        """, (location_id,))
        
        stock_items = []
        for row in cur.fetchall():
            stock_items.append({
                'id': row[0],
                'qty_available': row[1],
                'qty_reserved': row[2],
                'batch_id': row[3],
                'expiry_date': row[4].isoformat() if row[4] else None,
                'product_id': row[5],
                'product_name': row[6],
                'sku': row[7],
                'barcode': row[8],
                'description': row[9],
                'batch_tracked': row[10],
                'bin_code': row[11],
                'total_qty': row[1] + row[2]
            })
        
        cur.close()
        
        return jsonify({
            'location': {
                'id': location_id,
                'code': full_code,
                'warehouse_code': warehouse_code,
                'area_code': area_code,
                'rack_code': rack_code,
                'level_number': level_number,
                'bin_number': bin_number,
                'warehouse_id': warehouse_id,
                'warehouse_name': warehouse_name,
                'warehouse_address': warehouse_address
            },
            'stock_items': stock_items,
            'total_items': len(stock_items)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scanner/transaction', methods=['POST'])
@login_required
def api_scanner_transaction():
    """API endpoint to create a transaction from scanner operations"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['stock_item_id', 'transaction_type', 'quantity_change', 'notes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        stock_item_id = data['stock_item_id']
        transaction_type = data['transaction_type']
        quantity_change = data['quantity_change']
        notes = data['notes']
        
        # Validate transaction type
        valid_types = ['receive', 'ship', 'adjust', 'transfer', 'reserve', 'release']
        if transaction_type not in valid_types:
            return jsonify({'error': f'Invalid transaction type. Must be one of: {", ".join(valid_types)}'}), 400
        
        # Validate quantity change
        if not isinstance(quantity_change, (int, float)) or quantity_change == 0:
            return jsonify({'error': 'Quantity change must be a non-zero number'}), 400
        
        # Get current stock item details
        cur = get_db_connection().cursor()
        cur.execute("""
            SELECT si.on_hand, si.qty_reserved, p.name as product_name, p.sku
            FROM stock_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.id = %s
        """, (stock_item_id,))
        
        stock_result = cur.fetchone()
        if not stock_result:
            return jsonify({'error': 'Stock item not found'}), 404
        
        current_available, current_reserved, product_name, sku = stock_result
        
        # Calculate new quantities based on transaction type
        new_available = current_available
        new_reserved = current_reserved
        
        if transaction_type == 'receive':
            new_available += quantity_change
        elif transaction_type == 'ship':
            if current_available < quantity_change:
                return jsonify({'error': f'Insufficient available stock. Available: {current_available}, Requested: {quantity_change}'}), 400
            new_available -= quantity_change
        elif transaction_type == 'adjust':
            new_available += quantity_change
        elif transaction_type == 'reserve':
            if current_available < quantity_change:
                return jsonify({'error': f'Insufficient available stock to reserve. Available: {current_available}, Requested: {quantity_change}'}), 400
            new_available -= quantity_change
            new_reserved += quantity_change
        elif transaction_type == 'release':
            if current_reserved < quantity_change:
                return jsonify({'error': f'Insufficient reserved stock to release. Reserved: {current_reserved}, Requested: {quantity_change}'}), 400
            new_reserved -= quantity_change
            new_available += quantity_change
        elif transaction_type == 'transfer':
            # For transfers, we assume it's moving from available to reserved or vice versa
            if quantity_change > 0:  # Moving to reserved
                if current_available < quantity_change:
                    return jsonify({'error': f'Insufficient available stock for transfer. Available: {current_available}, Requested: {quantity_change}'}), 400
                new_available -= quantity_change
                new_reserved += quantity_change
            else:  # Moving from reserved to available
                quantity_change = abs(quantity_change)
                if current_reserved < quantity_change:
                    return jsonify({'error': f'Insufficient reserved stock for transfer. Reserved: {current_reserved}, Requested: {quantity_change}'}), 400
                new_reserved -= quantity_change
                new_available += quantity_change
        
        # Ensure quantities don't go negative
        if new_available < 0 or new_reserved < 0:
            return jsonify({'error': 'Transaction would result in negative stock quantities'}), 400
        
        # Update stock item
        cur.execute("""
            UPDATE stock_items 
            SET on_hand = %s, qty_reserved = %s
            WHERE id = %s
        """, (new_available, new_reserved, stock_item_id))
        
        # Create transaction record
        cur.execute("""
            INSERT INTO stock_transactions 
            (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            stock_item_id,
            transaction_type,
            quantity_change,
            current_available + current_reserved,
            new_available + new_reserved,
            notes,
            current_user.id
        ))
        
        transaction_id = cur.fetchone()[0]
        
        # Commit transaction
        cur.connection.commit()
        cur.close()
        
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'stock_item': {
                'id': stock_item_id,
                'product_name': product_name,
                'sku': sku,
                'new_available': new_available,
                'new_reserved': new_reserved,
                'new_total': new_available + new_reserved
            },
            'transaction': {
                'type': transaction_type,
                'quantity_change': quantity_change,
                'notes': notes
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bin/<bin_code>', methods=['GET'])
@login_required
def api_bin_details(bin_code):
    """API endpoint to get bin details and associated stock items"""
    try:
        # Validate bin code format (B followed by numbers)
        if not bin_code or not bin_code.startswith('B') or not bin_code[1:].isdigit():
            return jsonify({'error': 'Invalid bin code format. Expected format: B followed by numbers (e.g., B0045)'}), 400
        
        # Get bin details and associated stock items
        cur = get_db_connection().cursor()
        
        # Find the bin and its location
        cur.execute("""
            SELECT 
                b.id as bin_id,
                b.code as bin_code,
                b.location_id,
                l.full_code as location_code,
                w.id as warehouse_id,
                w.name as warehouse_name,
                w.code as warehouse_code,
                w.address as warehouse_address
            FROM bins b
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            WHERE b.code = %s
        """, (bin_code,))
        
        bin_result = cur.fetchone()
        if not bin_result:
            return jsonify({'error': f'Bin {bin_code} not found'}), 404
        
        bin_id, bin_code, location_id, location_code, warehouse_id, warehouse_name, warehouse_code, warehouse_address = bin_result
        
        # Check if this bin has any stock items
        cur.execute("""
            SELECT 
                si.id,
                si.on_hand,
                si.qty_reserved,
                si.batch_id,
                si.expiry_date,
                p.id as product_id,
                p.name as product_name,
                p.sku,
                p.barcode,
                p.description,
                p.batch_tracked
            FROM stock_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.bin_id = %s
            ORDER BY p.name
        """, (bin_id,))
        
        stock_items = []
        for row in cur.fetchall():
            stock_items.append({
                'id': row[0],
                'qty_available': row[1],
                'qty_reserved': row[2],
                'batch_id': row[3],
                'expiry_date': row[4].isoformat() if row[4] else None,
                'product_id': row[5],
                'product_name': row[6],
                'sku': row[7],
                'barcode': row[8],
                'description': row[9],
                'batch_tracked': row[10],
                'total_qty': row[1] + row[2]
            })
        
        cur.close()
        
        return jsonify({
            'bin': {
                'id': bin_id,
                'code': bin_code,
                'location_id': location_id,
                'location_code': location_code,
                'warehouse_id': warehouse_id,
                'warehouse_name': warehouse_name,
                'warehouse_code': warehouse_code,
                'warehouse_address': warehouse_address
            },
            'stock_items': stock_items,
            'total_items': len(stock_items),
            'has_stock': len(stock_items) > 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bin/<bin_code>/assign-stock', methods=['POST'])
@login_required
def api_assign_stock_to_bin(bin_code):
    """API endpoint to assign a stock item to a bin"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['product_id', 'quantity', 'batch_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        product_id = data['product_id']
        quantity = data['quantity']
        batch_id = data.get('batch_id')
        expiry_date = data.get('expiry_date')
        
        # Validate quantity
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            return jsonify({'error': 'Quantity must be a positive number'}), 400
        
        cur = get_db_connection().cursor()
        
        # Check if bin exists
        cur.execute("SELECT id FROM bins WHERE code = %s", (bin_code,))
        bin_result = cur.fetchone()
        if not bin_result:
            return jsonify({'error': f'Bin {bin_code} not found'}), 404
        
        bin_id = bin_result[0]
        
        # Check if product exists
        cur.execute("SELECT id, name FROM products WHERE id = %s", (product_id,))
        product_result = cur.fetchone()
        if not product_result:
            return jsonify({'error': 'Product not found'}), 404
        
        product_name = product_result[1]
        
        # Check if bin already has stock items
        cur.execute("SELECT COUNT(*) FROM stock_items WHERE bin_id = %s", (bin_id,))
        existing_count = cur.fetchone()[0]
        
        if existing_count > 0:
            return jsonify({'error': f'Bin {bin_code} already has stock items assigned. Please use a different bin or move existing items first.'}), 400
        
        # Create new stock item
        cur.execute("""
            INSERT INTO stock_items 
            (product_id, bin_id, on_hand, qty_reserved, batch_id, expiry_date, received_date)
            VALUES (%s, %s, %s, 0, %s, %s, NOW())
            RETURNING id
        """, (product_id, bin_id, quantity, batch_id, expiry_date))
        
        stock_item_id = cur.fetchone()[0]
        
        # Create transaction record
        cur.execute("""
            INSERT INTO stock_transactions 
            (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            stock_item_id,
            'receive',
            quantity,
            0,
            quantity,
            f'Initial stock assignment to bin {bin_code}',
            current_user.id
        ))
        
        transaction_id = cur.fetchone()[0]
        
        # Commit transaction
        cur.connection.commit()
        cur.close()
        
        return jsonify({
            'success': True,
            'stock_item_id': stock_item_id,
            'transaction_id': transaction_id,
            'message': f'Successfully assigned {quantity} units of {product_name} to bin {bin_code}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/available', methods=['GET'])
@login_required
def api_available_products():
    """API endpoint to get available products for bin assignment"""
    try:
        cur = get_db_connection().cursor()
        
        cur.execute("""
            SELECT 
                id,
                name,
                sku,
                barcode,
                description
            FROM products
            ORDER BY name
        """)
        
        products = []
        for row in cur.fetchall():
            products.append({
                'id': row[0],
                'name': row[1],
                'sku': row[2],
                'barcode': row[3],
                'description': row[4]
            })
        
        cur.close()
        
        return jsonify({'products': products})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bin/<bin_code>/change-location', methods=['POST'])
@login_required
def api_change_bin_location(bin_code):
    """API endpoint to change a bin's location"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'location_id' not in data:
            return jsonify({'error': 'Missing required field: location_id'}), 400
        
        location_id = data['location_id']
        
        cur = get_db_connection().cursor()
        
        # Check if bin exists
        cur.execute("SELECT id FROM bins WHERE code = %s", (bin_code,))
        bin_result = cur.fetchone()
        if not bin_result:
            return jsonify({'error': f'Bin {bin_code} not found'}), 404
        
        bin_id = bin_result[0]
        
        # Check if location exists
        cur.execute("SELECT id, full_code FROM locations WHERE id = %s", (location_id,))
        location_result = cur.fetchone()
        if not location_result:
            return jsonify({'error': 'Location not found'}), 404
        
        location_code = location_result[1]
        
        # Update bin location
        cur.execute("""
            UPDATE bins 
            SET location_id = %s, updated_at = NOW()
            WHERE id = %s
        """, (location_id, bin_id))
        
        # Create transaction record for the location change
        cur.execute("""
            INSERT INTO stock_transactions 
            (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id)
            SELECT 
                si.id,
                'transfer',
                0,
                si.on_hand + si.qty_reserved,
                si.on_hand + si.qty_reserved,
                %s,
                %s
            FROM stock_items si
            WHERE si.bin_id = %s
        """, (f'Bin {bin_code} moved to location {location_code}', current_user.id, bin_id))
        
        # Commit transaction
        cur.connection.commit()
        cur.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully moved bin {bin_code} to location {location_code}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/locations/available', methods=['GET'])
@login_required
def api_available_locations():
    """API endpoint to get available locations for bin assignment"""
    try:
        cur = get_db_connection().cursor()
        
        cur.execute("""
            SELECT 
                l.id,
                l.full_code,
                w.name as warehouse_name,
                w.code as warehouse_code
            FROM locations l
            JOIN warehouses w ON l.warehouse_id = w.id
            ORDER BY w.name, l.full_code
        """)
        
        locations = []
        for row in cur.fetchall():
            locations.append({
                'id': row[0],
                'full_code': row[1],
                'warehouse_name': row[2],
                'warehouse_code': row[3]
            })
        
        cur.close()
        
        return jsonify({'locations': locations})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("* Starting Inventory Management App...")
    print("* PostgreSQL Database Mode")
    print("* Login credentials:")
    print("   - Admin: admin / admin123")
    print("   - Manager: manager / manager123") 
    print("   - Worker: worker / worker123")
    print("* App running at: http://127.0.0.1:5001")
    app.run(debug=True, host='127.0.0.1', port=5001)
