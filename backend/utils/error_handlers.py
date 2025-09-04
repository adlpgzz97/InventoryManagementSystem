"""
Error handling utilities and decorators for consistent error handling.
Provides decorators and functions to standardize error responses.
"""

import functools
import logging
from typing import Callable, Any, Dict, Optional
from flask import jsonify, request, current_app

from backend.exceptions import (
    InventoryAppException, ValidationError, DatabaseError, NotFoundError,
    AuthenticationError, AuthorizationError, BusinessLogicError
)

logger = logging.getLogger(__name__)


def handle_errors(f: Callable) -> Callable:
    """
    Decorator to handle exceptions and return consistent error responses.
    
    Usage:
        @app.route('/api/products')
        @handle_errors
        def get_products():
            # Your route logic here
            pass
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {f.__name__}: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'details': e.details
            }), 400
        except NotFoundError as e:
            logger.info(f"Resource not found in {f.__name__}: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'details': e.details
            }), 404
        except AuthenticationError as e:
            logger.warning(f"Authentication error in {f.__name__}: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code
            }), 401
        except AuthorizationError as e:
            logger.warning(f"Authorization error in {f.__name__}: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'details': e.details
            }), 403
        except BusinessLogicError as e:
            logger.warning(f"Business logic error in {f.__name__}: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'details': e.details
            }), 422
        except DatabaseError as e:
            logger.error(f"Database error in {f.__name__}: {e.message}")
            return jsonify({
                'success': False,
                'error': 'Database operation failed',
                'error_code': 'DATABASE_ERROR'
            }), 500
        except InventoryAppException as e:
            logger.error(f"Application error in {f.__name__}: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'details': e.details
            }), 500
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'error_code': 'INTERNAL_ERROR'
            }), 500
    return decorated_function


def handle_api_errors(f: Callable) -> Callable:
    """
    Decorator specifically for API endpoints with additional logging.
    
    Usage:
        @app.route('/api/products')
        @handle_api_errors
        def get_products():
            # Your API logic here
            pass
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Log the request
        logger.info(f"API request: {request.method} {request.path} from {request.remote_addr}")
        
        try:
            result = f(*args, **kwargs)
            # Log successful response
            logger.info(f"API response: {request.method} {request.path} - Success")
            return result
        except Exception as e:
            # Log error with request details
            logger.error(
                f"API error: {request.method} {request.path} - {type(e).__name__}: {str(e)}",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', 'Unknown')
                },
                exc_info=True
            )
            raise
    return decorated_function


def log_errors(f: Callable) -> Callable:
    """
    Decorator to log errors without changing the response.
    
    Usage:
        @app.route('/api/products')
        @log_errors
        def get_products():
            # Your route logic here
            pass
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            raise
    return decorated_function


def create_error_response(
    message: str,
    error_code: str = "GENERAL_ERROR",
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        error_code: Error code for client handling
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'success': False,
        'error': message,
        'error_code': error_code
    }
    
    if details:
        response['details'] = details
    
    return jsonify(response), status_code


def handle_validation_errors(validation_errors: Dict[str, list]) -> tuple:
    """
    Create a standardized validation error response.
    
    Args:
        validation_errors: Dictionary of field names to error messages
        
    Returns:
        Tuple of (response, status_code)
    """
    return create_error_response(
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        status_code=400,
        details={'fields': validation_errors}
    )


def setup_error_handlers(app):
    """
    Set up global error handlers for the Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        return create_error_response(
            "Bad request",
            "BAD_REQUEST",
            400
        )
    
    @app.errorhandler(401)
    def unauthorized(error):
        return create_error_response(
            "Unauthorized",
            "UNAUTHORIZED",
            401
        )
    
    @app.errorhandler(403)
    def forbidden(error):
        return create_error_response(
            "Forbidden",
            "FORBIDDEN",
            403
        )
    
    @app.errorhandler(404)
    def not_found(error):
        return create_error_response(
            "Resource not found",
            "NOT_FOUND",
            404
        )
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return create_error_response(
            "Method not allowed",
            "METHOD_NOT_ALLOWED",
            405
        )
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        return create_error_response(
            "Unprocessable entity",
            "UNPROCESSABLE_ENTITY",
            422
        )
    
    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        return create_error_response(
            "Internal server error",
            "INTERNAL_ERROR",
            500
        )
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return create_error_response(
            "Internal server error",
            "INTERNAL_ERROR",
            500
        )
