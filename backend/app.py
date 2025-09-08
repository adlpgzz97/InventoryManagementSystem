"""
Inventory Management System - Flask Application
Main application entry point with blueprint registration
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_login import LoginManager
import logging
import os
from datetime import datetime

# Import configuration
from backend.config import config

# Import models
from backend.models.user import User

# Import route blueprints
from backend.routes.simple_auth import auth_bp
from backend.routes import (
    dashboard_bp, 
    products_bp, 
    stock_bp, 
    warehouses_bp, 
    scanner_bp,
    transactions_bp
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_app(config_class=None):
    """Application factory pattern"""
    app = Flask(__name__, template_folder='views')
    
    # Load configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        # Use centralized configuration
        app.config.update(config.FLASK_CONFIG)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = config.LOGIN_MESSAGE
    login_manager.login_message_category = 'info'
    
    # Configure session for desktop app compatibility
    app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP in desktop app
    app.config['SESSION_COOKIE_HTTPONLY'] = False  # Allow JavaScript access for PyWebView
    app.config['SESSION_COOKIE_SAMESITE'] = None  # Disable SameSite for PyWebView
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow localhost
    app.config['SESSION_COOKIE_PATH'] = '/'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
    app.config['SESSION_COOKIE_NAME'] = 'inventory_session'  # Custom session name
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        try:
            return User.get_by_id(user_id)
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {e}")
            return None
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register middleware
    register_middleware(app)
    
    # Register global context processors
    register_context_processors(app)
    
    # Database connections will be created on-demand for faster startup
    
    logger.info("Flask application created successfully")
    return app


def register_blueprints(app):
    """Register all application blueprints"""
    try:
        # Authentication routes
        app.register_blueprint(auth_bp)
        
        # Dashboard routes (root level)
        app.register_blueprint(dashboard_bp)
        
        # Management routes
        app.register_blueprint(products_bp)
        app.register_blueprint(stock_bp)
        app.register_blueprint(warehouses_bp)
        app.register_blueprint(transactions_bp)
        
        # Scanner routes
        app.register_blueprint(scanner_bp)
        
        logger.info("All blueprints registered successfully")
        
    except Exception as e:
        logger.error(f"Error registering blueprints: {e}")
        raise


def register_error_handlers(app):
    """Register global error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors"""
        logger.warning(f"404 error: {request.url}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Page not found'}), 404
        return render_template('error.html', 
                             message='Page not found',
                             error_code=404), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"500 error: {error}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error.html', 
                             message='Internal server error',
                             error_code=500), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors"""
        logger.warning(f"403 error: {request.url}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Access forbidden'}), 403
        return render_template('error.html', 
                             message='Access forbidden',
                             error_code=403), 403
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 errors"""
        logger.warning(f"401 error: {request.url}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Access forbidden'}), 401
        return render_template('error.html', 
                             message='Access forbidden',
                             error_code=401), 401
    
    logger.info("Error handlers registered successfully")


def register_middleware(app):
    """Register application middleware"""
    
    @app.before_request
    def before_request():
        """Execute before each request - simplified for faster startup"""
        # Add request start time for performance monitoring
        request.start_time = datetime.now()
    
    @app.after_request
    def after_request(response):
        """Execute after each request - simplified"""
        # Add basic security headers
        from backend.utils.simple_security import SimpleSecurityUtils
        response = SimpleSecurityUtils.add_security_headers(response)
        
        # Add cache-busting headers for PyWebView compatibility
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    logger.info("Middleware registered successfully")


def register_context_processors(app):
    """Register global context processors"""
    
    @app.context_processor
    def inject_user_info():
        """Inject user information into all templates"""
        from flask_login import current_user
        
        if current_user.is_authenticated:
            return {
                'current_user': current_user,
                'user_role': current_user.role if hasattr(current_user, 'role') else 'user'
            }
        return {
            'current_user': None,
            'user_role': None
        }
    
    @app.context_processor
    def inject_app_info():
        """Inject application information into all templates"""
        return {
            'app_name': 'Inventory Management System',
            'app_version': '1.0.0',
            'current_year': datetime.now().year
        }
    
    @app.context_processor
    def inject_csrf_token():
        """Inject CSRF token into all templates"""
        from backend.utils.simple_security import SimpleSecurityUtils
        return {
            'csrf_token': SimpleSecurityUtils.generate_csrf_token()
        }
    
    logger.info("Context processors registered successfully")


# Create the application instance
app = create_app()

# Root route redirect
@app.route('/')
def index():
    """Root route - redirect to login for simple authentication"""
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    else:
        return redirect(url_for('auth.login'))


@app.route('/api/cors-preflight', methods=['OPTIONS'])
def cors_preflight():
    """Handle CORS preflight requests for desktop apps"""
    response = jsonify({'status': 'ok'})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response


@app.route('/api/health')
def health_check():
    """Health check endpoint for desktop app connectivity"""
    return jsonify({
        'status': 'healthy',
        'message': 'Flask backend is running',
        'timestamp': datetime.now().isoformat(),
        'session_enabled': True,
        'cors_enabled': True,
        'config': {
            'environment': os.environ.get('FLASK_ENV', 'development'),
            'debug': config.DEBUG,
            'database_connected': True  # TODO: Add actual database health check
        }
    })


@app.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors"""
    return '', 204  # No content response

@app.route('/api/test-desktop')
def test_desktop():
    """Test endpoint specifically for desktop app connectivity"""
    return jsonify({
        'success': True,
        'message': 'Desktop app can reach Flask backend',
        'timestamp': datetime.now().isoformat(),
        'request_headers': dict(request.headers),
        'request_cookies': dict(request.cookies),
        'request_method': request.method,
        'request_url': request.url
    })


if __name__ == '__main__':
    logger.info("Starting Inventory Management System...")
    logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    logger.info(f"Debug mode: {config.DEBUG}")
    logger.info(f"Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    
    # Use configuration for host and port
    app.run(
        host=config.APP_HOST,
        port=config.APP_PORT,
        debug=config.DEBUG
    )
