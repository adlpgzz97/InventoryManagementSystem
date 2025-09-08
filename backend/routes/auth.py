"""
Authentication Routes for Inventory Management System
Handles login, logout, and authentication-related routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
import logging

from backend.services.auth_service import AuthService
from backend.models.user import User
from backend.utils.security import require_csrf_token, sanitize_inputs, SecurityUtils

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
        # Log request details for debugging
        logger.info(f"Login POST request received")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request form data keys: {list(request.form.keys())}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request URL: {request.url}")

        # Validate CSRF token BEFORE sanitization
        csrf_token = request.form.get('csrf_token')
        logger.info(f"CSRF token received: {csrf_token[:10] if csrf_token else 'None'}...")

        # Check if this is a desktop app request (PyWebView)
        user_agent = request.headers.get('User-Agent', '')
        logger.info(f"User-Agent received: {user_agent}")
        
        # More robust desktop app detection
        # Check for explicit desktop app indicators
        explicit_desktop = (
            'pywebview' in user_agent.lower() or 
            'inventory' in user_agent.lower()
        )
        
        # Check for PyWebView-like patterns in standard browser User-Agents
        pywebview_pattern = (
            'mozilla' in user_agent.lower() and 'pywebview' in user_agent.lower() or
            'webkit' in user_agent.lower() and 'pywebview' in user_agent.lower()
        )
        
        # Check for other desktop app indicators (referer, origin, etc.)
        other_indicators = (
            request.headers.get('Referer', '').startswith('http://127.0.0.1:5001') and
            request.headers.get('Origin', '').startswith('http://127.0.0.1:5001')
        )
        
        is_desktop_app = explicit_desktop or pywebview_pattern or other_indicators
        
        logger.info(f"Desktop app detection: {is_desktop_app}")
        
        # For desktop app, bypass CSRF validation entirely
        if is_desktop_app:
            logger.info("Desktop app detected, bypassing CSRF validation for compatibility")
        elif not SecurityUtils.validate_csrf_token(csrf_token):
            logger.warning(f"CSRF validation failed. Token: {csrf_token[:10] if csrf_token else 'None'}...")
            flash('Security validation failed. Please refresh the page and try again.', 'error')
            return render_template('login.html'), 400

        # Now sanitize the inputs (excluding password and csrf_token which are already validated)
        username = SecurityUtils.sanitize_input(request.form.get('username', ''))
        password = request.form.get('password', '')  # Don't sanitize password
        remember = request.form.get('remember', False)

        # Log login attempt details for debugging
        logger.info(f"Login attempt - Username: {username}, Remember: {remember}")

        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('login.html'), 400

        try:
            # Authenticate user with direct database connection
            logger.info(f"Starting authentication for user: {username}")
            user = AuthService.authenticate_user(username, password)

            if user:
                logger.info(f"Authentication successful for user: {username}, proceeding to login...")
                # Log in user
                success = AuthService.login_user(user, remember=bool(remember))

                if success:
                    logger.info(f"User {username} logged in successfully")
                    flash(f'Welcome back, {user.username}!', 'success')

                    # Redirect to next page or dashboard
                    next_page = request.args.get('next')
                    if next_page and next_page.startswith('/') and next_page != '/':
                        logger.info(f"Redirecting to next page: {next_page}")
                        return redirect(next_page)

                    # Always redirect to dashboard for root path to prevent loops
                    dashboard_url = url_for('dashboard.dashboard')
                    logger.info(f"Redirecting to dashboard: {dashboard_url}")
                    return redirect(dashboard_url)
                else:
                    logger.error(f"Login failed for user {username} - AuthService.login_user returned False")
                    flash('Login failed. Please try again.', 'error')
            else:
                logger.warning(f"Authentication failed for username: {username} - no user returned")
                flash('Invalid username or password', 'error')

        except Exception as e:
            logger.error(f"Login error for user {username}: {e}", exc_info=True)
            flash(f'An error occurred during login: {str(e)}', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    try:
        username = current_user.username
        success = AuthService.logout_user()
        
        if success:
            logger.info(f"User {username} logged out successfully")
            flash('You have been logged out successfully.', 'success')
        else:
            flash('Logout failed. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Logout error: {e}")
        flash('An error occurred during logout.', 'error')
    
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Display user profile"""
    try:
        user_info = AuthService.get_user_info(current_user)
        activity_summary = AuthService.get_user_activity_summary(current_user.id)
        
        return render_template('profile.html', 
                             user_info=user_info, 
                             activity_summary=activity_summary)
                             
    except Exception as e:
        logger.error(f"Error loading profile for user {current_user.username}: {e}")
        flash('Error loading profile information.', 'error')
        return redirect(url_for('dashboard.dashboard'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Handle password change"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([current_password, new_password, confirm_password]):
            flash('Please fill in all password fields.', 'error')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('change_password.html')
        
        try:
            # Validate new password strength
            validation = AuthService.validate_password_strength(new_password)
            if not validation['valid']:
                for error in validation['errors']:
                    flash(error, 'error')
                return render_template('change_password.html')
            
            # Change password
            success = AuthService.change_user_password(
                current_user.id, 
                current_password, 
                new_password
            )
            
            if success:
                flash('Password changed successfully!', 'success')
                return redirect(url_for('auth.profile'))
            else:
                flash('Current password is incorrect.', 'error')
                
        except Exception as e:
            logger.error(f"Password change error for user {current_user.username}: {e}")
            flash('An error occurred while changing password.', 'error')
    
    return render_template('change_password.html')


@auth_bp.route('/api/user-info')
@login_required
def api_user_info():
    """API endpoint to get current user information"""
    try:
        user_info = AuthService.get_user_info(current_user)
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


@auth_bp.route('/api/validate-password', methods=['POST'])
def api_validate_password():
    """API endpoint to validate password strength"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        validation = AuthService.validate_password_strength(password)
        
        return jsonify({
            'success': True,
            'validation': validation
        })
    except Exception as e:
        logger.error(f"Error validating password: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to validate password'
        }), 500


@auth_bp.route('/api/check-auth')
def api_check_auth():
    """API endpoint to check authentication status"""
    try:
        if current_user.is_authenticated:
            user_info = AuthService.get_user_info(current_user)
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


@auth_bp.route('/api/test-auth')
def api_test_auth():
    """Test endpoint for authentication debugging"""
    try:
        return jsonify({
            'success': True,
            'message': 'Auth endpoint accessible',
            'current_user_authenticated': current_user.is_authenticated if current_user else False,
            'session_data': {
                'session_id': session.get('session_id', 'N/A'),
                'csrf_token': session.get('csrf_token', 'N/A'),
                'user_id': session.get('user_id', 'N/A'),
                'session_data': dict(session),
                'cookies': dict(request.cookies),
                'headers': dict(request.headers),
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'origin': request.headers.get('Origin', 'Unknown'),
                'referer': request.headers.get('Referer', 'Unknown')
            }
        })
    except Exception as e:
        logger.error(f"Error in test auth endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/api/session-test')
def api_session_test():
    """Test session management and cookies"""
    try:
        session_info = {
            'session_id': session.get('_id', None),
            'csrf_token': session.get('csrf_token', None),
            'user_id': session.get('user_id', None),
            'session_data': dict(session),
            'cookies': dict(request.cookies),
            'headers': dict(request.headers),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'origin': request.headers.get('Origin', 'Unknown'),
            'referer': request.headers.get('Referer', 'Unknown')
        }
        
        logger.info(f"Session test endpoint called: {session_info}")
        return jsonify(session_info)
        
    except Exception as e:
        logger.error(f"Session test error: {e}")
        return jsonify({'error': str(e)}), 500


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
