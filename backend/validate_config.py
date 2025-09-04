"""
Configuration Validation Script
Validates that all required environment variables are set and configuration is valid
"""

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from config import config, ConfigError

def validate_environment():
    """Validate environment variables and configuration"""
    print("Validating Inventory Management System Configuration...")
    print("=" * 60)
    
    # Check required environment variables
    required_vars = [
        'DB_PASSWORD',
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nTIP: Please set these variables in your .env file")
        return False
    
    # Try to load configuration
    try:
        app_config = config
        print("SUCCESS: Configuration loaded successfully")
        print(f"   - Environment: {os.environ.get('FLASK_ENV', 'development')}")
        print(f"   - Database: {app_config.DB_HOST}:{app_config.DB_PORT}/{app_config.DB_NAME}")
        print(f"   - App Host: {app_config.APP_HOST}:{app_config.APP_PORT}")
        print(f"   - Debug Mode: {app_config.DEBUG}")
        
        # Check for security warnings
        if app_config.SECRET_KEY == 'dev-secret-key-change-in-production':
            print("WARNING: Using default SECRET_KEY - change in production!")
        
        if not app_config.SESSION_COOKIE_SECURE:
            print("INFO: Session cookies not secure (OK for development)")
        
        return True
        
    except ConfigError as e:
        print(f"ERROR: Configuration validation failed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error loading configuration: {e}")
        return False

def check_database_connection():
    """Check if database connection can be established"""
    print("\nTesting database connection...")
    
    try:
        from backend.utils.database import test_connection
        if test_connection():
            print("SUCCESS: Database connection successful")
            return True
        else:
            print("ERROR: Database connection failed")
            return False
    except Exception as e:
        print(f"ERROR: Database connection test error: {e}")
        return False

def main():
    """Main validation function"""
    print("Inventory Management System - Configuration Validator")
    print("=" * 60)
    
    # Check if .env file exists
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        print("SUCCESS: .env file found")
    else:
        print("WARNING: .env file not found - using system environment variables")
        print("TIP: Consider creating a .env file for local development")
    
    # Validate configuration
    if not validate_environment():
        print("\nERROR: Configuration validation failed")
        sys.exit(1)
    
    # Test database connection
    if not check_database_connection():
        print("\nERROR: Database connection failed")
        print("TIP: Please check your database configuration and ensure PostgreSQL is running")
        sys.exit(1)
    
    print("\nSUCCESS: All validation checks passed!")
    print("Your application is ready to run")
    
    return True

if __name__ == '__main__':
    main()
