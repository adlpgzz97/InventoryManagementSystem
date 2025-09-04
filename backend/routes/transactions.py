"""
Transactions Routes for Inventory Management System
Handles stock transaction management pages and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging
from datetime import datetime

from backend.models.stock import StockTransaction, StockItem
from backend.models.product import Product
from backend.models.warehouse import Warehouse, Location, Bin
from backend.models.user import User
from backend.utils.database import execute_query

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')


@transactions_bp.route('/')
@login_required
def transactions_list():
    """Stock transactions page"""
    try:
        # Get transactions with related data
        query = """
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
        """
        
        transactions = execute_query(query, fetch_all=True)
        
        # Get summary statistics
        stats_query = """
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
        """
        
        stats = execute_query(stats_query, fetch_one=True)
        
        return render_template('transactions.html', 
                             transactions=transactions, 
                             stats=stats)
                             
    except Exception as e:
        logger.error(f"Error loading transactions: {e}")
        flash('Error loading transactions', 'error')
        return redirect(url_for('dashboard.dashboard'))


@transactions_bp.route('/api', methods=['GET'])
@login_required
def api_transactions():
    """Get transactions with filtering and pagination"""
    try:
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
        total_count = execute_query(count_query, params, fetch_one=True)['count']
        
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
        transactions = execute_query(query, params + [per_page, offset], fetch_all=True)
        
        return jsonify({
            'transactions': transactions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500


@transactions_bp.route('/api/<transaction_id>', methods=['GET'])
@login_required
def api_transaction_detail(transaction_id):
    """Get detailed information about a specific transaction"""
    try:
        query = """
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
        """
        
        transaction = execute_query(query, (transaction_id,), fetch_one=True)
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        return jsonify(transaction)
        
    except Exception as e:
        logger.error(f"Error fetching transaction detail: {e}")
        return jsonify({'error': 'Failed to fetch transaction detail'}), 500


@transactions_bp.route('/api', methods=['POST'])
@login_required
def api_create_transaction():
    """Create a new stock transaction"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['stock_item_id', 'transaction_type', 'quantity_change']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate transaction type
        valid_types = ['receive', 'ship', 'adjust', 'transfer', 'reserve', 'release']
        if data['transaction_type'] not in valid_types:
            return jsonify({'error': f'Invalid transaction type. Must be one of: {", ".join(valid_types)}'}), 400
        
        # Get current stock levels
        stock_query = """
            SELECT on_hand, qty_reserved 
            FROM stock_items 
            WHERE id = %s
        """
        stock_item = execute_query(stock_query, (data['stock_item_id'],), fetch_one=True)
        
        if not stock_item:
            return jsonify({'error': 'Stock item not found'}), 404
        
        quantity_before = stock_item['on_hand']
        quantity_after = quantity_before + data['quantity_change']
        
        # Validate stock levels for outgoing transactions
        if data['transaction_type'] in ['ship', 'transfer'] and quantity_after < 0:
            return jsonify({'error': 'Insufficient stock for this transaction'}), 400
        
        # Update stock levels
        update_query = """
            UPDATE stock_items 
            SET on_hand = %s 
            WHERE id = %s
        """
        execute_query(update_query, (quantity_after, data['stock_item_id']))
        
        # Create transaction record
        transaction_query = """
            INSERT INTO stock_transactions 
            (stock_item_id, transaction_type, quantity_change, quantity_before, quantity_after, notes, user_id, reference_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        transaction_result = execute_query(
            transaction_query, 
            (
                data['stock_item_id'],
                data['transaction_type'],
                data['quantity_change'],
                quantity_before,
                quantity_after,
                data.get('notes', ''),
                current_user.id,
                data.get('reference_id')
            ),
            fetch_one=True
        )
        
        transaction_id = transaction_result['id']
        
        return jsonify({
            'message': 'Transaction created successfully',
            'transaction_id': transaction_id,
            'quantity_before': quantity_before,
            'quantity_after': quantity_after
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        return jsonify({'error': 'Failed to create transaction'}), 500


@transactions_bp.route('/api/warehouses')
@login_required
def api_warehouses():
    """Get warehouses for filter dropdown"""
    try:
        warehouses = Warehouse.get_all()
        return jsonify({
            'warehouses': [w.to_dict() for w in warehouses]
        })
    except Exception as e:
        logger.error(f"Error fetching warehouses: {e}")
        return jsonify({'error': 'Failed to fetch warehouses'}), 500


@transactions_bp.route('/api/stock-items')
@login_required
def api_stock_items():
    """Get stock items for transaction form"""
    try:
        query = """
            SELECT 
                si.id,
                p.name as product_name,
                p.sku,
                w.name as warehouse_name,
                l.full_code,
                si.on_hand
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            LEFT JOIN bins b ON si.bin_id = b.id
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            ORDER BY p.name, w.name
        """
        
        stock_items = execute_query(query, fetch_all=True)
        
        return jsonify({
            'stock_items': stock_items
        })
    except Exception as e:
        logger.error(f"Error fetching stock items: {e}")
        return jsonify({'error': 'Failed to fetch stock items'}), 500
