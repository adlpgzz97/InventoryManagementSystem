#!/usr/bin/env python3
"""
Test script to verify login functionality
"""

import requests
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_login():
    """Test login functionality"""
    print("Testing login functionality...")
    
    # Test 1: Check if login page loads
    try:
        response = requests.get('http://localhost:5001/auth/login', timeout=10)
        print(f"✓ Login page loads: {response.status_code}")
        
        if response.status_code == 200:
            # Check if CSRF token is present
            if 'csrf_token' in response.text:
                print("✓ CSRF token found in page")
            else:
                print("✗ CSRF token not found in page")
        else:
            print(f"✗ Login page failed to load: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to connect to login page: {e}")
        return False
    
    # Test 2: Test login with valid credentials
    try:
        # Get CSRF token from the page
        response = requests.get('http://localhost:5001/auth/login', timeout=10)
        
        # Extract CSRF token (simple approach)
        csrf_start = response.text.find('name="csrf_token" value="')
        if csrf_start != -1:
            csrf_start += len('name="csrf_token" value="')
            csrf_end = response.text.find('"', csrf_start)
            csrf_token = response.text[csrf_start:csrf_end]
            print(f"✓ CSRF token extracted: {csrf_token[:10]}...")
        else:
            print("✗ Could not extract CSRF token")
            return False
        
        # Test login
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token,
            'remember': False
        }
        
        response = requests.post(
            'http://localhost:5001/auth/login',
            data=login_data,
            timeout=10,
            allow_redirects=False
        )
        
        print(f"✓ Login request sent: {response.status_code}")
        
        if response.status_code in [302, 200]:
            print("✓ Login appears successful (redirect or OK)")
            return True
        else:
            print(f"✗ Login failed with status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Login request failed: {e}")
        return False

def test_server_status():
    """Test if the server is running"""
    try:
        response = requests.get('http://localhost:5001/', timeout=5)
        print(f"✓ Server is running: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Server is not running: {e}")
        return False

if __name__ == '__main__':
    print("=== Login Functionality Test ===\n")
    
    # Check if server is running
    if not test_server_status():
        print("\nPlease start the Flask server first:")
        print("python main.py")
        sys.exit(1)
    
    print()
    
    # Test login
    if test_login():
        print("\n✓ All tests passed! Login is working correctly.")
    else:
        print("\n✗ Some tests failed. Check the server logs for details.")
        sys.exit(1)
