"""
Security Configuration for Inventory Management System
Defines security policies, password requirements, and session settings
"""

from typing import Dict, Any

# Password Policy Configuration
PASSWORD_POLICY = {
    'min_length': 8,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_numbers': True,
    'require_special_chars': False,  # Optional but recommended
    'max_age_days': 90,  # Password expiration
    'history_count': 5,  # Prevent reuse of last 5 passwords
}

# Session Security Configuration
SESSION_SECURITY = {
    'timeout_minutes': 60,  # Session timeout
    'absolute_timeout_hours': 24,  # Maximum session duration
    'regenerate_id': True,  # Regenerate session ID on login
    'secure_cookies': False,  # Set to True in production with HTTPS
    'http_only': True,  # Prevent XSS access to cookies
    'same_site': 'Lax',  # CSRF protection
}

# Rate Limiting Configuration
RATE_LIMITS = {
    'login_attempts': {
        'max_attempts': 5,
        'window_minutes': 15,
        'lockout_minutes': 30
    },
    'api_requests': {
        'max_requests': 100,
        'window_minutes': 1
    }
}

# Input Validation Rules
INPUT_VALIDATION = {
    'username': {
        'min_length': 3,
        'max_length': 50,
        'pattern': r'^[a-zA-Z0-9_-]+$',
        'description': 'Username must be 3-50 characters, alphanumeric with _ and -'
    },
    'email': {
        'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'description': 'Must be a valid email address'
    },
    'product_sku': {
        'min_length': 3,
        'max_length': 20,
        'pattern': r'^[A-Z0-9_-]+$',
        'description': 'SKU must be 3-20 characters, uppercase alphanumeric with _ and -'
    }
}

# Security Headers Configuration
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
}

# Audit Logging Configuration
AUDIT_LOGGING = {
    'enabled': True,
    'log_level': 'INFO',
    'events': [
        'user_login',
        'user_logout',
        'user_password_change',
        'data_creation',
        'data_modification',
        'data_deletion',
        'admin_actions'
    ]
}

def get_security_config() -> Dict[str, Any]:
    """Get complete security configuration"""
    return {
        'password_policy': PASSWORD_POLICY,
        'session_security': SESSION_SECURITY,
        'rate_limits': RATE_LIMITS,
        'input_validation': INPUT_VALIDATION,
        'security_headers': SECURITY_HEADERS,
        'audit_logging': AUDIT_LOGGING
    }
