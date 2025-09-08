"""
Simple Security utilities for Inventory Management System
Minimal security for local use with basic CSRF protection
"""

import html
import secrets
from typing import Optional
from flask import request, session, current_app
import logging

logger = logging.getLogger(__name__)


class SimpleSecurityUtils:
    """Simple security utility functions for local use"""
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a CSRF token"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(16)
        return session['csrf_token']
    
    @staticmethod
    def validate_csrf_token(token: str) -> bool:
        """Validate CSRF token"""
        if not token:
            return False
        
        session_token = session.get('csrf_token')
        if not session_token:
            return False
        
        return token == session_token
    
    @staticmethod
    def sanitize_input(input_data: str) -> str:
        """Basic input sanitization to prevent XSS"""
        if not input_data:
            return ""
        
        # HTML escape content
        clean_text = html.escape(str(input_data))
        
        return clean_text.strip()
    
    @staticmethod
    def add_security_headers(response):
        """Add basic security headers"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
