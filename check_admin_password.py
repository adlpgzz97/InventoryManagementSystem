#!/usr/bin/env python3
"""
Script to check admin user password hash and verify authentication
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.utils.database import execute_query
from backend.models.user import User
import bcrypt

def check_admin_password():
    """Check admin user's password hash"""
    try:
        # Get admin user details
        result = execute_query(
            "SELECT id, username, password_hash, role FROM users WHERE username = 'admin'", 
            fetch_one=True
        )
        
        if result:
            print(f"Admin user found:")
            print(f"  Username: {result['username']}")
            print(f"  Role: {result['role']}")
            print(f"  ID: {result['id']}")
            print(f"  Password hash: {result['password_hash']}")
            
            # Check if password hash starts with bcrypt format
            if result['password_hash'].startswith('$2b$'):
                print("  Password hash format: Valid bcrypt format")
            else:
                print("  Password hash format: INVALID - not bcrypt format")
                
            return result
        else:
            print("Admin user not found")
            return None
            
    except Exception as e:
        print(f"Error checking admin password: {e}")
        return None

def test_admin_auth():
    """Test admin authentication with different passwords"""
    passwords_to_test = ['admin123', 'admin', 'password', '123456']
    
    print("\n--- Testing Admin Authentication ---")
    
    for password in passwords_to_test:
        try:
            user = User.authenticate('admin', password)
            if user:
                print(f"  ✓ SUCCESS with password: '{password}'")
                return password
            else:
                print(f"  ✗ FAILED with password: '{password}'")
        except Exception as e:
            print(f"  ✗ ERROR with password '{password}': {e}")
    
    return None

def update_admin_password():
    """Update admin user password to 'admin123'"""
    try:
        print("\n--- Updating Admin Password ---")
        
        # Create new password hash
        new_password = "admin123"
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update password in database
        result = execute_query(
            "UPDATE users SET password_hash = %s WHERE username = 'admin' RETURNING id",
            (new_hash,),
            fetch_one=True
        )
        
        if result:
            print("  ✓ Admin password updated successfully")
            return True
        else:
            print("  ✗ Failed to update admin password")
            return False
            
    except Exception as e:
        print(f"  ✗ Error updating admin password: {e}")
        return False

if __name__ == "__main__":
    print("=== Admin Password Check Script ===\n")
    
    # Check current admin password
    admin_data = check_admin_password()
    
    if admin_data:
        # Test authentication
        working_password = test_admin_auth()
        
        if not working_password:
            print("\nNo working password found. Updating admin password...")
            if update_admin_password():
                print("\n--- Testing Updated Password ---")
                test_admin_auth()
        else:
            print(f"\nWorking password found: '{working_password}'")
    else:
        print("Cannot proceed without admin user")
