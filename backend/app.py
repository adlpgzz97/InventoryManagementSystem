"""
Inventory Management System - Flask Application
Main application entry point with blueprint registration
"""

from flask import Flask, render_template, jsonify
from flask_login import LoginManager
import logging
import os

# Import configuration
from config import Config

# Import models
from models.user import User

# Import route blueprints
from routes import (
    auth_bp, 
    dashboard_bp, 
    products_bp, 
    stock_bp, 
    warehouses_bp, 
    scanner_bp
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__, template_folder='views')
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
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
        if request.is_xhr:
            return jsonify({'error': 'Page not found'}), 404
        return render_template('error.html', 
                             message='Page not found',
                             error_code=404), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"500 error: {error}")
        if request.is_xhr:
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error.html', 
                             message='Internal server error',
                             error_code=500), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 errors"""
        logger.warning(f"403 error: {request.url}")
        if request.is_xhr:
            return jsonify({'error': 'Access forbidden'}), 403
        return render_template('error.html', 
                             message='Access forbidden',
                             error_code=403), 403
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 errors"""
        logger.warning(f"401 error: {request.url}")
        if request.is_xhr:
            return jsonify({'error': 'Authentication required'}), 401
        return render_template('error.html', 
                             message='Authentication required',
                             error_code=401), 401
    
    logger.info("Error handlers registered successfully")


def register_middleware(app):
    """Register application middleware"""
    
    @app.before_request
    def before_request():
        """Execute before each request"""
        # Log request information
        logger.info(f"Request: {request.method} {request.url}")
        
        # Add request start time for performance monitoring
        request.start_time = datetime.now()
    
    @app.after_request
    def after_request(response):
        """Execute after each request"""
        # Calculate request duration
        if hasattr(request, 'start_time'):
            duration = (datetime.now() - request.start_time).total_seconds()
            logger.info(f"Response: {response.status_code} - Duration: {duration:.3f}s")
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
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
    
    logger.info("Context processors registered successfully")


# Create the application instance
app = create_app()

# Import required modules for error handlers and middleware
from flask import request
from datetime import datetime

if __name__ == '__main__':
    logger.info("Starting Inventory Management System...")
    logger.info(f"Environment: {app.config.get('ENV', 'production')}")
    logger.info(f"Debug mode: {app.config.get('DEBUG', False)}")
    
    app.run(
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )
