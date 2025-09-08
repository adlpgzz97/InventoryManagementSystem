"""
API routes for category management
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.models.category import Category
import logging

logger = logging.getLogger(__name__)

api_categories_bp = Blueprint('api_categories', __name__, url_prefix='/api')

@api_categories_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """Get all categories"""
    try:
        categories = Category.get_all()
        return jsonify([category.to_dict() for category in categories])
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'error': 'Failed to get categories'}), 500

@api_categories_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    """Create a new category"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        code = data.get('code', '').strip().upper()
        description = data.get('description', '').strip()
        
        if not code:
            return jsonify({'error': 'Category code is required'}), 400
        
        # Validate code format
        if not code.replace('_', '').isalnum():
            return jsonify({'error': 'Category code must contain only letters, numbers, and underscores'}), 400
        
        # Check if category already exists
        existing_category = Category.get_by_code(code)
        if existing_category:
            return jsonify({'error': f'Category with code "{code}" already exists'}), 400
        
        # Create new category
        category = Category.create(code=code, description=description)
        
        if category:
            return jsonify({
                'success': True,
                'category': category.to_dict(),
                'message': f'Category "{code}" created successfully'
            })
        else:
            return jsonify({'error': 'Failed to create category'}), 500
            
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return jsonify({'error': 'Failed to create category'}), 500

@api_categories_bp.route('/categories/<category_id>', methods=['GET'])
@login_required
def get_category(category_id):
    """Get a specific category by ID"""
    try:
        category = Category.get_by_id(category_id)
        if category:
            return jsonify(category.to_dict())
        else:
            return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        logger.error(f"Error getting category {category_id}: {e}")
        return jsonify({'error': 'Failed to get category'}), 500

@api_categories_bp.route('/categories/<category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """Update a category"""
    try:
        category = Category.get_by_id(category_id)
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        code = data.get('code', '').strip().upper()
        description = data.get('description', '').strip()
        
        if not code:
            return jsonify({'error': 'Category code is required'}), 400
        
        # Validate code format
        if not code.replace('_', '').isalnum():
            return jsonify({'error': 'Category code must contain only letters, numbers, and underscores'}), 400
        
        # Check if another category with the same code exists
        existing_category = Category.get_by_code(code)
        if existing_category and existing_category.id != category_id:
            return jsonify({'error': f'Category with code "{code}" already exists'}), 400
        
        # Update category
        success = category.update(code=code, description=description)
        
        if success:
            return jsonify({
                'success': True,
                'category': category.to_dict(),
                'message': f'Category "{code}" updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update category'}), 500
            
    except Exception as e:
        logger.error(f"Error updating category {category_id}: {e}")
        return jsonify({'error': 'Failed to update category'}), 500

@api_categories_bp.route('/categories/<category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """Delete a category"""
    try:
        category = Category.get_by_id(category_id)
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Delete category (this will set product category_id to NULL due to ON DELETE SET NULL)
        success = category.delete()
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Category "{category.code}" deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete category'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting category {category_id}: {e}")
        return jsonify({'error': 'Failed to delete category'}), 500
