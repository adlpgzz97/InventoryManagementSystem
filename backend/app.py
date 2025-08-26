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
                INSERT INTO stock_items (product_id, location_id, qty_available, qty_reserved, batch_id, expiry_date)
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
                new_available = existing_stock['qty_available'] + qty_available
                new_reserved = existing_stock['qty_reserved'] + qty_reserved
                
                cur.execute("""
                    UPDATE stock_items 
                    SET qty_available = %s, qty_reserved = %s 
                    WHERE id = %s
                """, (new_available, new_reserved, existing_stock['id']))
                
                conn.commit()
                cur.close()
                conn.close()
                
                # Log transaction
                log_stock_transaction(
                    existing_stock['id'], 'receive', qty_available, 
                    existing_stock['qty_available'], new_available
                )
                
                return {'id': existing_stock['id']}
            else:
                # Create new stock record (no batch info for non-batch-tracked)
                cur.execute("""
                    INSERT INTO stock_items (product_id, location_id, qty_available, qty_reserved, batch_id, expiry_date)
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
        
        # Get stock data with product and location information
        cur.execute("""
            SELECT 
                si.*,
                p.name as product_name, 
                p.sku as product_sku,
                l.aisle, 
                l.bin,
                w.name as warehouse_name
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN locations l ON si.location_id = l.id
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
                'aisle': item_dict.get('aisle', ''),
                'bin': item_dict.get('bin', ''),
                'warehouses': {
                    'name': item_dict.get('warehouse_name', 'Unknown')
                }
            }
            stock_data.append(item_dict)
        
        # Calculate low stock items
        low_stock_items = [item for item in stock_data if item['qty_available'] < 10]
        
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
        cur.execute("SELECT * FROM products ORDER BY created_at DESC")
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
        
        # Get stock items with product and location information
        cur.execute("""
            SELECT 
                si.*,
                p.name as product_name, 
                p.sku as product_sku,
                l.aisle, 
                l.bin,
                w.name as warehouse_name
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN locations l ON si.location_id = l.id
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
            # Create nested structure for template compatibility
            item_dict['products'] = {
                'name': item_dict.get('product_name', 'Unknown'),
                'sku': item_dict.get('product_sku', 'N/A')
            }
            item_dict['locations'] = {
                'aisle': item_dict.get('aisle', ''),
                'bin': item_dict.get('bin', ''),
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
            GROUP BY w.id, w.name, w.address
            ORDER BY w.name
        """)
        warehouses_data = cur.fetchall()
        
        # Get locations for each warehouse
        warehouse_list = []
        for warehouse in warehouses_data:
            warehouse_dict = dict(warehouse)
            
            # Get locations for this warehouse
            cur.execute("SELECT * FROM locations WHERE warehouse_id = %s ORDER BY aisle, bin", (warehouse['id'],))
            locations = cur.fetchall()
            warehouse_dict['locations'] = [dict(loc) for loc in locations] if locations else []
            
            warehouse_list.append(warehouse_dict)
        
        cur.close()
        conn.close()
        return render_template('warehouses.html', warehouses=warehouse_list)
    except Exception as e:
        flash(f'Error loading warehouses: {e}', 'error')
        return render_template('warehouses.html', warehouses=[])

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
        
        # Get stock data with product and location information for analysis
        cur.execute("""
            SELECT 
                si.*,
                p.name as product_name, 
                p.sku as product_sku,
                p.batch_tracked,
                l.aisle, 
                l.bin,
                w.name as warehouse_name
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN locations l ON si.location_id = l.id
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
                'aisle': item_dict.get('aisle', ''),
                'bin': item_dict.get('bin', ''),
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
                qty = item.get('qty_available', 0)
                
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
                            location = f"{item['locations'].get('aisle', '')}{item['locations'].get('bin', '')}"
                        
                        low_stock_alerts.append({
                            'product_name': item['products'].get('name', 'Unknown'),
                            'sku': item['products'].get('sku', 'N/A'),
                            'location': f"{warehouse_name} - {location}",
                            'qty_available': qty
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
                                location = f"{item['locations'].get('aisle', '')}{item['locations'].get('bin', '')}"
                            
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
        low_stock_alerts.sort(key=lambda x: x['qty_available'])
        expiry_alerts.sort(key=lambda x: x['days_to_expiry'])
        
        # Batch analytics (if batch tracking is used)
        batch_analytics = None
        batch_tracked_items = [item for item in (stock_data or []) if item.get('batch_id')]
        if batch_tracked_items:
            batch_analytics = analyze_batch_data(batch_tracked_items)
        
        # Detailed stock report
        detailed_stock_report = []
        for item in (stock_data or []):
            qty_available = item.get('qty_available', 0)
            
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
                'qty_available': qty_available,
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
            
            # Update via PostgREST
            response = postgrest_request(f'products?id=eq.{product_id}', 'PATCH', data)
            
            if is_modal:
                return '<div class="alert alert-success">Product updated successfully!</div>'
            else:
                flash('Product updated successfully!', 'success')
                return redirect(url_for('products'))
        
        else:
            # GET request - show form
            product_data = postgrest_request(f'products?id=eq.{product_id}&select=*')
            if not product_data:
                flash('Product not found.', 'error')
                return redirect(url_for('products'))
            
            product = product_data[0]
            
            if is_modal:
                return render_template('edit_product_modal.html', product=product)
            else:
                return render_template('edit_product.html', product=product)
                
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
                'qty_available': int(request.form.get('qty_available')),
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
            
            # Update via direct database query
            conn = get_db_connection()
            cur = conn.cursor()
            
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
        response = postgrest_request(f'products?id=eq.{product_id}', 'DELETE')
        flash('Product deleted successfully!', 'success')
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
        response = postgrest_request(f'stock_items?id=eq.{stock_id}', 'DELETE')
        flash('Stock item deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting stock item: {e}', 'error')
    
    return redirect(url_for('stock'))

@app.route('/delete/warehouse/<warehouse_id>', methods=['POST'])
@login_required
def delete_warehouse(warehouse_id):
    """Delete warehouse"""
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied. Management privileges required.', 'error')
        return redirect(url_for('warehouses'))
    
    try:
        response = postgrest_request(f'warehouses?id=eq.{warehouse_id}', 'DELETE')
        flash('Warehouse deleted successfully!', 'success')
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
            
            # Create locations based on the new aisle data format
            aisles_data = request.form.get('aisles_data')
            if aisles_data:
                try:
                    aisles = json.loads(aisles_data)
                    for aisle in aisles:
                        aisle_name = aisle['name']
                        bin_count = aisle['bins']
                        
                        # Create bins for this aisle
                        for bin_num in range(1, bin_count + 1):
                            cur.execute("INSERT INTO locations (warehouse_id, aisle, bin) VALUES (%s, %s, %s)", 
                                       (warehouse_id, aisle_name, str(bin_num)))
                    
                    conn.commit()
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"Error parsing aisles data: {e}")
                    # Fallback to old format if new format fails
                    sample_aisles = request.form.get('sample_aisles', 'A,B').split(',')
                    sample_bins = int(request.form.get('sample_bins', 3))
                    
                    for aisle in sample_aisles:
                        aisle = aisle.strip()
                        if aisle:
                            for bin_num in range(1, min(sample_bins + 1, 21)):
                                cur.execute("INSERT INTO locations (warehouse_id, aisle, bin) VALUES (%s, %s, %s)", 
                                           (warehouse_id, aisle, str(bin_num)))
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

if __name__ == '__main__':
    print("* Starting Inventory Management App...")
    print("* PostgreSQL Database Mode")
    print("* Login credentials:")
    print("   - Admin: admin / admin123")
    print("   - Manager: manager / manager123") 
    print("   - Worker: worker / worker123")
    print("* App running at: http://127.0.0.1:5001")
    app.run(debug=True, host='127.0.0.1', port=5001)
