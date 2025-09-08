"""
Simple Authentication Routes for Inventory Management System
Minimal authentication for local use with basic CSRF protection
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
import logging

from backend.services.simple_auth_service import SimpleAuthService

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        # Skip CSRF validation for PyWebView/local development
        # csrf_token = request.form.get('csrf_token')
        # CSRF validation disabled for PyWebView compatibility

        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('login.html')

        try:
            logger.info(f"Attempting login for user: {username}")
            
            # Authenticate user
            user = SimpleAuthService.authenticate_user(username, password)
            logger.info(f"Authentication result: {user is not None}")

            if user:
                logger.info(f"User authenticated, attempting login: {user.username}")
                # Log in user
                success = SimpleAuthService.login_user(user, remember=bool(remember))
                logger.info(f"Login success: {success}")

                if success:
                    flash(f'Welcome back, {user.username}!', 'success')
                    logger.info(f"Login successful, redirecting to dashboard")
                    
                    # Redirect to next page or dashboard
                    next_page = request.args.get('next')
                    if next_page and next_page.startswith('/') and next_page != '/':
                        return redirect(next_page)
                    
                    return redirect(url_for('dashboard.dashboard'))
                else:
                    flash('Login failed. Please try again.', 'error')
                    logger.error("Login failed - SimpleAuthService.login_user returned False")
            else:
                flash('Invalid username or password', 'error')
                logger.warning(f"Authentication failed for user: {username}")

        except Exception as e:
            logger.error(f"Login error for user {username}: {e}", exc_info=True)
            flash('An error occurred during login. Please try again.', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    try:
        username = current_user.username
        success = SimpleAuthService.logout_user()
        
        if success:
            flash('You have been logged out successfully.', 'success')
        else:
            flash('Logout failed. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Logout error: {e}")
        flash('An error occurred during logout.', 'error')
    
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/user-info')
@login_required
def api_user_info():
    """API endpoint to get current user information"""
    try:
        user_info = SimpleAuthService.get_user_info(current_user)
        return jsonify({
            'success': True,
            'user': user_info
        })
    except Exception as e:
        logger.error(f"Error getting user info for API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user information'
        }), 500


@auth_bp.route('/api/check-auth')
def api_check_auth():
    """API endpoint to check authentication status"""
    try:
        if current_user.is_authenticated:
            user_info = SimpleAuthService.get_user_info(current_user)
            return jsonify({
                'authenticated': True,
                'user': user_info
            })
        else:
            return jsonify({
                'authenticated': False,
                'user': None
            })
    except Exception as e:
        logger.error(f"Error checking authentication: {e}")
        return jsonify({
            'authenticated': False,
            'error': 'Failed to check authentication'
        }), 500


# Error handlers for authentication routes
@auth_bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access"""
    if request.is_xhr:
        return jsonify({'error': 'Authentication required'}), 401
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('auth.login'))


@auth_bp.errorhandler(403)
def forbidden(error):
    """Handle forbidden access"""
    if request.is_xhr:
        return jsonify({'error': 'Insufficient permissions'}), 403
    flash('You do not have permission to access this page.', 'error')
    return redirect(url_for('dashboard.dashboard'))
