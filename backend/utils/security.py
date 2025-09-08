"""
Security utilities for Inventory Management System
Handles CSRF protection, input sanitization, and security headers
"""

import re
import html
import hashlib
import secrets
from typing import Optional, Dict, Any
from flask import request, session, current_app
import logging

logger = logging.getLogger(__name__)


class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a CSRF token"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
        return session['csrf_token']
    
    @staticmethod
    def validate_csrf_token(token: str) -> bool:
        """Validate CSRF token with desktop app compatibility"""
        if not token:
            logger.warning("CSRF token is empty")
            return False
        
        session_token = session.get('csrf_token')
        if not session_token:
            logger.warning("No CSRF token in session")
            return False
        
        # Check if tokens match
        is_valid = token == session_token
        
        if not is_valid:
            logger.warning(f"CSRF token mismatch. Received: {token[:10]}..., Session: {session_token[:10]}...")
        
        return is_valid
    
    @staticmethod
    def sanitize_input(input_data: str) -> str:
        """Sanitize user input to prevent XSS"""
        if not input_data:
            return ""
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', str(input_data))
        
        # HTML escape remaining content
        clean_text = html.escape(clean_text)
        
        # Remove potentially dangerous characters
        clean_text = re.sub(r'[<>"\']', '', clean_text)
        
        return clean_text.strip()
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all string values in a dictionary"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = SecurityUtils.sanitize_input(value)
            elif isinstance(value, dict):
                sanitized[key] = SecurityUtils.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [SecurityUtils.sanitize_input(str(item)) if isinstance(item, str) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        errors = []
        warnings = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        elif len(password) < 12:
            warnings.append("Consider using a longer password (12+ characters)")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            warnings.append("Consider adding special characters for better security")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'score': max(0, 100 - len(errors) * 20 - len(warnings) * 5)
        }
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt"""
        if not salt:
            salt = secrets.token_hex(16)
        
        # Use SHA-256 with salt
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed, salt
    
    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """Verify password against hash"""
        expected_hash, _ = SecurityUtils.hash_password(password, salt)
        return secrets.compare_digest(hashed, expected_hash)
    
    @staticmethod
    def add_security_headers(response):
        """Add security headers to response"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com; img-src 'self' data: https:;"
        
        # Add HSTS header for HTTPS
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response


def require_csrf_token(f):
    """Decorator to require CSRF token validation"""
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not SecurityUtils.validate_csrf_token(token):
                logger.warning(f"CSRF token validation failed for {request.endpoint}")
                return {'error': 'CSRF token validation failed'}, 403
        return f(*args, **kwargs)
    return decorated_function


def sanitize_inputs(f):
    """Decorator to sanitize all input data"""
    def decorated_function(*args, **kwargs):
        # Sanitize form data (excluding CSRF token which needs to remain unchanged)
        if request.form:
            sanitized_form = {}
            for key, value in request.form.items():
                # Skip CSRF token and other security-related fields
                if key in ['csrf_token', 'password']:
                    sanitized_form[key] = value
                elif isinstance(value, str):
                    sanitized_form[key] = SecurityUtils.sanitize_input(value)
                else:
                    sanitized_form[key] = value
            # Replace the form data with sanitized version
            request._cached_form = sanitized_form

        # Sanitize JSON data
        if request.is_json and request.get_json():
            request._cached_json = SecurityUtils.sanitize_dict(request.get_json())

        # Sanitize query parameters
        if request.args:
            request.args = SecurityUtils.sanitize_dict(request.args)

        return f(*args, **kwargs)
    return decorated_function
