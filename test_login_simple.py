#!/usr/bin/env python3
"""
Simple login test script to verify authentication flow
"""

import requests
import sys
from urllib.parse import urljoin

def test_login():
    """Test the login functionality"""
    base_url = "http://127.0.0.1:5001"
    
    print("=== Testing Login Functionality ===")
    
    # Test 1: Get login page and extract CSRF token
    print("\n1. Getting login page...")
    try:
        response = requests.get(f"{base_url}/auth/login", timeout=10)
        if response.status_code != 200:
            print(f"✗ Failed to get login page: {response.status_code}")
            return False
        
        print("✓ Login page loaded successfully")
        
        # Extract CSRF token
        if 'name="csrf_token" value="' not in response.text:
            print("✗ CSRF token not found in login page")
            return False
        
        csrf_start = response.text.find('name="csrf_token" value="')
        csrf_start += len('name="csrf_token" value="')
        csrf_end = response.text.find('"', csrf_start)
        csrf_token = response.text[csrf_start:csrf_end]
        
        print(f"✓ CSRF token extracted: {csrf_token[:10]}...")
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error getting login page: {e}")
        return False
    
    # Test 2: Attempt login with admin credentials
    print("\n2. Attempting login...")
    try:
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrf_token': csrf_token
        }
        
        response = requests.post(
            f"{base_url}/auth/login",
            data=login_data,
            allow_redirects=False,  # Don't follow redirects
            timeout=10
        )
        
        print(f"Login response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location')
            print(f"✓ Login successful! Redirecting to: {redirect_url}")
            
            # Test 3: Follow the redirect to dashboard
            print("\n3. Testing dashboard access...")
            try:
                dashboard_response = requests.get(
                    urljoin(base_url, redirect_url),
                    cookies=response.cookies,
                    timeout=10
                )
                
                if dashboard_response.status_code == 200:
                    print("✓ Dashboard accessed successfully")
                    if "dashboard" in dashboard_response.text.lower():
                        print("✓ Dashboard content confirmed")
                        return True
                    else:
                        print("✗ Dashboard content not found")
                        return False
                else:
                    print(f"✗ Dashboard access failed: {dashboard_response.status_code}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                print(f"✗ Error accessing dashboard: {e}")
                return False
                
        else:
            print(f"✗ Login failed with status: {response.status_code}")
            print(f"Response content: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error during login: {e}")
        return False

if __name__ == "__main__":
    print("Starting login test...")
    success = test_login()
    
    if success:
        print("\n🎉 All tests passed! Login is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed! Login has issues.")
        sys.exit(1)
