"""
Create default admin user for Inventory Management System
Simple script to create an admin user based on the SCHEMA
"""

import bcrypt
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.utils.database import execute_query
from backend.config import config

def create_default_user():
    """Create a default admin user"""
    try:
        # Check if admin user already exists
        result = execute_query(
            "SELECT id FROM users WHERE username = %s",
            ('admin',),
            fetch_one=True
        )
        
        if result:
            print("Admin user already exists!")
            return True
        
        # Create admin user
        password = "admin123"  # Simple password for local development
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        result = execute_query(
            """
            INSERT INTO users (username, password_hash, role) 
            VALUES (%s, %s, %s) 
            RETURNING id, username, role
            """,
            ('admin', password_hash, 'admin'),
            fetch_one=True
        )
        
        if result:
            print(f"Default admin user created successfully!")
            print(f"Username: admin")
            print(f"Password: admin123")
            print(f"Role: admin")
            return True
        else:
            print("Failed to create admin user")
            return False
            
    except Exception as e:
        print(f"Error creating default user: {e}")
        return False

if __name__ == "__main__":
    print("Creating default admin user...")
    success = create_default_user()
    if success:
        print("Setup complete!")
    else:
        print("Setup failed!")
        sys.exit(1)
