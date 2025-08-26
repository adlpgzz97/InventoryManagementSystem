#!/usr/bin/env python3
"""
Simple test script to verify application setup and database connectivity
"""

import sys
import os

def test_imports():
    """Test if all required packages can be imported"""
    print("Testing imports...")
    
    try:
        import flask
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return False
    
    try:
        import flask_login
        print("✓ Flask-Login imported successfully")
    except ImportError as e:
        print(f"✗ Flask-Login import failed: {e}")
        return False
    
    try:
        import psycopg2
        print("✓ psycopg2 imported successfully")
    except ImportError as e:
        print(f"✗ psycopg2 import failed: {e}")
        print("  Please run: pip install psycopg2-binary")
        return False
    
    try:
        import bcrypt
        print("✓ bcrypt imported successfully")
    except ImportError as e:
        print(f"✗ bcrypt import failed: {e}")
        return False
    
    try:
        import requests
        print("✓ requests imported successfully")
    except ImportError as e:
        print(f"✗ requests import failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connectivity"""
    print("\nTesting database connection...")
    
    try:
        import psycopg2
        import psycopg2.extras
        
        # Database configuration
        DB_CONFIG = {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'port': os.environ.get('DB_PORT', '5432'),
            'database': os.environ.get('DB_NAME', 'inventory_db'),
            'user': os.environ.get('DB_USER', 'postgres'),
            'password': os.environ.get('DB_PASSWORD', 'TatUtil97==')
        }
        
        print(f"Connecting to database: {DB_CONFIG['database']} on {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Test basic query
        cur.execute("SELECT version()")
        version = cur.fetchone()
        print(f"✓ Database connected successfully")
        print(f"  PostgreSQL version: {version[0]}")
        
        # Test if required tables exist
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'products', 'stock_items', 'warehouses', 'locations')
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        
        required_tables = ['users', 'products', 'stock_items', 'warehouses', 'locations']
        found_tables = [table[0] for table in tables]
        
        print(f"  Required tables: {required_tables}")
        print(f"  Found tables: {found_tables}")
        
        missing_tables = set(required_tables) - set(found_tables)
        if missing_tables:
            print(f"  ✗ Missing tables: {missing_tables}")
            print("  Please run the database schema setup")
            cur.close()
            conn.close()
            return False
        else:
            print("  ✓ All required tables found")
        
        # Test if users exist
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        print(f"  Users in database: {user_count}")
        
        if user_count == 0:
            print("  ⚠ No users found - you may need to run sample data setup")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("  Please check:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'inventory_db' exists")
        print("  3. User credentials are correct")
        print("  4. Environment variables are set")
        return False

def test_flask_app():
    """Test if Flask app can be imported and configured"""
    print("\nTesting Flask app...")
    
    try:
        # Add backend directory to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
        
        # Try to import the app
        from app import app
        
        print("✓ Flask app imported successfully")
        print(f"  App name: {app.name}")
        print(f"  Debug mode: {app.debug}")
        
        # Test if templates directory exists
        template_dir = os.path.join(os.path.dirname(__file__), 'backend', 'views')
        if os.path.exists(template_dir):
            print("✓ Templates directory found")
        else:
            print("✗ Templates directory not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Flask app import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Inventory Management App - Connection Test")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
    
    # Test database connection
    if not test_database_connection():
        all_passed = False
    
    # Test Flask app
    if not test_flask_app():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed! Application should work correctly.")
        print("\nTo run the application:")
        print("1. Activate virtual environment: venv\\Scripts\\activate")
        print("2. Run: python backend/app.py")
        print("3. Open: http://127.0.0.1:5001")
    else:
        print("✗ Some tests failed. Please fix the issues above before running the app.")
        print("\nCommon fixes:")
        print("1. Install missing packages: pip install -r requirements.txt")
        print("2. Setup database: psql -U postgres -d inventory_db -f db/schema.sql")
        print("3. Run migration: psql -U postgres -d inventory_db -f db/migration_batch_tracking.sql")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
