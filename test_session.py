#!/usr/bin/env python3
"""
Test script to debug session management issues
"""

import requests
import sys
import os

def test_session():
    """Test session management"""
    print("Testing session management...")
    
    # Create a session object to maintain cookies
    session = requests.Session()
    
    # Test 1: Check session state before login
    try:
        response = session.get('http://localhost:5001/auth/api/session-test', timeout=10)
        print(f"✓ Session test before login: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Session ID: {data.get('session_id', 'None')}")
            print(f"  CSRF Token: {data.get('csrf_token', 'None')}")
            print(f"  Cookies: {len(data.get('cookies', {}))}")
        else:
            print(f"  Response: {response.text[:200]}...")
    except Exception as e:
        print(f"✗ Session test failed: {e}")
        return False
    
    # Test 2: Try to access dashboard (should redirect to login)
    try:
        response = session.get('http://localhost:5001/dashboard', timeout=10, allow_redirects=False)
        print(f"✓ Dashboard access test: {response.status_code}")
        if response.status_code == 302:
            print(f"  Redirect location: {response.headers.get('Location', 'None')}")
        else:
            print(f"  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"✗ Dashboard test failed: {e}")
        return False
    
    # Test 3: Get login page and extract CSRF token
    try:
        response = session.get('http://localhost:5001/auth/login', timeout=10)
        print(f"✓ Login page access: {response.status_code}")
        
        if response.status_code == 200:
            # Extract CSRF token
            csrf_start = response.text.find('name="csrf_token" value="')
            if csrf_start != -1:
                csrf_start += len('name="csrf_token" value="')
                csrf_end = response.text.find('"', csrf_start)
                csrf_token = response.text[csrf_start:csrf_end]
                print(f"  CSRF token found: {csrf_token[:10]}...")
            else:
                print("  ✗ CSRF token not found")
                return False
        else:
            print(f"  ✗ Login page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Login page test failed: {e}")
        return False
    
    # Test 4: Try login with valid credentials
    try:
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token,
            'remember': False
        }
        
        response = session.post(
            'http://localhost:5001/auth/login',
            data=login_data,
            timeout=10,
            allow_redirects=False
        )
        
        print(f"✓ Login attempt: {response.status_code}")
        
        if response.status_code == 302:
            print(f"  Redirect location: {response.headers.get('Location', 'None')}")
            
            # Check if we got a session cookie
            cookies = dict(session.cookies)
            print(f"  Session cookies: {cookies}")
            
            # Test 5: Try to access dashboard again
            response = session.get('http://localhost:5001/dashboard', timeout=10, allow_redirects=False)
            print(f"✓ Dashboard access after login: {response.status_code}")
            
            if response.status_code == 200:
                print("  ✓ Successfully accessed dashboard!")
                return True
            else:
                print(f"  ✗ Still can't access dashboard: {response.status_code}")
                return False
        else:
            print(f"  ✗ Login failed with status: {response.status_code}")
            print(f"  Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"✗ Login test failed: {e}")
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
    print("=== Session Management Test ===\n")
    
    # Check if server is running
    if not test_server_status():
        print("\nPlease start the Flask server first:")
        print("python main.py")
        sys.exit(1)
    
    print()
    
    # Test session management
    if test_session():
        print("\n✓ All tests passed! Session management is working correctly.")
    else:
        print("\n✗ Some tests failed. Check the server logs for details.")
        sys.exit(1)
