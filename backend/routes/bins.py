"""
Bins Routes for Inventory Management System
Provides an overview of bins, their locations, and contents
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import logging

from backend.utils.database import execute_query

logger = logging.getLogger(__name__)

bins_bp = Blueprint('bins', __name__, url_prefix='/bins')


@bins_bp.route('/')
@login_required
def bins_list():
    """Bins overview page"""
    try:
        search_term = (request.args.get('search') or '').strip()
        warehouse_id = (request.args.get('warehouse') or '').strip()

        params = []
        filters = []

        if warehouse_id:
            filters.append('w.id = %s')
            params.append(warehouse_id)

        if search_term:
            filters.append('(b.code ILIKE %s OR l.full_code ILIKE %s)')
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''

        query = f"""
            SELECT 
                b.id AS bin_id,
                b.code AS bin_code,
                l.id AS location_id,
                l.full_code AS location_code,
                w.id AS warehouse_id,
                w.name AS warehouse_name,
                COALESCE(SUM(si.on_hand), 0) AS on_hand,
                COALESCE(SUM(si.qty_reserved), 0) AS qty_reserved,
                COUNT(DISTINCT si.product_id) AS product_count
            FROM bins b
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            LEFT JOIN stock_items si ON si.bin_id = b.id
            {where_clause}
            GROUP BY b.id, b.code, l.id, l.full_code, w.id, w.name
            ORDER BY w.name NULLS LAST, l.full_code NULLS LAST, b.code
        """

        rows = execute_query(query, tuple(params) if params else None, fetch_all=True) or []

        return render_template('bins.html', bins=rows, search_term=search_term, selected_warehouse=warehouse_id)
    except Exception as e:
        logger.error(f"Error loading bins page: {e}")
        return render_template('bins.html', bins=[], search_term='', selected_warehouse='')


@bins_bp.route('/api/list')
@login_required
def api_bins_list():
    """API endpoint returning bins with location and content summary"""
    try:
        search_term = (request.args.get('search') or '').strip()
        warehouse_id = (request.args.get('warehouse') or '').strip()
        limit = request.args.get('limit', type=int)

        params = []
        filters = []

        if warehouse_id:
            filters.append('w.id = %s')
            params.append(warehouse_id)

        if search_term:
            filters.append('(b.code ILIKE %s OR l.full_code ILIKE %s)')
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ''

        query = f"""
            SELECT 
                b.id AS bin_id,
                b.code AS bin_code,
                l.id AS location_id,
                l.full_code AS location_code,
                w.id AS warehouse_id,
                w.name AS warehouse_name,
                COALESCE(SUM(si.on_hand), 0) AS on_hand,
                COALESCE(SUM(si.qty_reserved), 0) AS qty_reserved,
                COUNT(DISTINCT si.product_id) AS product_count
            FROM bins b
            LEFT JOIN locations l ON b.location_id = l.id
            LEFT JOIN warehouses w ON l.warehouse_id = w.id
            LEFT JOIN stock_items si ON si.bin_id = b.id
            {where_clause}
            GROUP BY b.id, b.code, l.id, l.full_code, w.id, w.name
            ORDER BY w.name NULLS LAST, l.full_code NULLS LAST, b.code
        """

        if limit and isinstance(limit, int) and limit > 0:
            query += "\nLIMIT %s"
            params.append(limit)

        rows = execute_query(query, tuple(params) if params else None, fetch_all=True) or []

        return jsonify({
            'success': True,
            'bins': rows,
            'total': len(rows)
        })
    except Exception as e:
        logger.error(f"Error in bins API: {e}")
        return jsonify({'success': False, 'error': 'Failed to load bins'}), 500


