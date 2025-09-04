#!/usr/bin/env python3
"""
Script to check existing users and create admin user if needed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.utils.database import execute_query
from backend.models.user import User
import bcrypt

def check_users():
    """Check existing users in the database"""
    try:
        # Check if users table exists and has data
        result = execute_query("SELECT COUNT(*) as count FROM users", fetch_one=True)
        if result:
            print(f"Total users in database: {result['count']}")
        
        # Get all users
        users = execute_query("SELECT id, username, role, created_at FROM users", fetch_all=True)
        if users:
            print("\nExisting users:")
            for user in users:
                print(f"  - {user['username']} (Role: {user['role']}, ID: {user['id']})")
        else:
            print("\nNo users found in database")
            
    except Exception as e:
        print(f"Error checking users: {e}")
        return False
    
    return True

def create_admin_user():
    """Create admin user if it doesn't exist"""
    try:
        # Check if admin user already exists
        admin_user = execute_query(
            "SELECT id FROM users WHERE username = 'admin'", 
            fetch_one=True
        )
        
        if admin_user:
            print("Admin user already exists")
            return True
        
        # Create admin user
        password = "admin123"
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
            print(f"Admin user created successfully: {result['username']} (Role: {result['role']})")
            return True
        else:
            print("Failed to create admin user")
            return False
            
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False

def test_authentication():
    """Test authentication for admin user"""
    try:
        user = User.authenticate('admin', 'admin123')
        if user:
            print(f"\nAuthentication test successful for {user.username}")
            return True
        else:
            print("\nAuthentication test failed")
            return False
            
    except Exception as e:
        print(f"Error testing authentication: {e}")
        return False

if __name__ == "__main__":
    print("=== User Management Script ===\n")
    
    # Check existing users
    if check_users():
        print("\n--- Creating Admin User ---")
        if create_admin_user():
            print("\n--- Testing Authentication ---")
            test_authentication()
        else:
            print("Failed to create admin user")
    else:
        print("Failed to check users")
