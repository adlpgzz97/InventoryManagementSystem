#!/usr/bin/env python3
"""
Test script to call the API endpoint with authentication
"""

import requests
import json

def login_and_test():
    """Login and then test the product details API endpoint"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # First, try to login
    login_url = "http://127.0.0.1:5000/auth/login"
    
    print("Attempting to login...")
    
    # Get the login page first to get any CSRF tokens if needed
    login_page_response = session.get(login_url)
    print(f"Login page status: {login_page_response.status_code}")
    
    # Try to login with the correct credentials
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = session.post(login_url, data=login_data)
    print(f"Login response status: {login_response.status_code}")
    print(f"Login response URL: {login_response.url}")
    
    # Check if login was successful (should redirect to dashboard)
    if 'dashboard' in login_response.url or login_response.status_code == 302:
        print("Login appears successful")
    else:
        print("Login may have failed, but continuing with test...")
        print("Login response content (first 500 chars):")
        print(login_response.text[:500])
    
    # Now test the product details API endpoint
    product_id = "7fbadf57-b5de-43b1-a174-6d6cb7c4cd51"
    api_url = f"http://127.0.0.1:5000/products/api/{product_id}/details"
    
    print(f"\nTesting authenticated API URL: {api_url}")
    
    try:
        response = session.get(api_url)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("Response Body (first 500 chars):")
            print(response.text[:500])
            if len(response.text) > 500:
                print("... (truncated)")
                
            # Try to parse as JSON
            try:
                json_data = response.json()
                print("Successfully parsed as JSON:")
                print(json.dumps(json_data, indent=2))
            except json.JSONDecodeError as e:
                print(f"Failed to parse as JSON: {e}")
        else:
            print("Response Body:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Connection Error: Flask app might not be running")
    except Exception as e:
        print(f"Error: {e}")

def test_debug_endpoint_with_auth():
    """Test the debug endpoint with authentication"""
    
    session = requests.Session()
    
    # Try to login first
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    session.post("http://127.0.0.1:5000/auth/login", data=login_data)
    
    # Test debug endpoint
    url = "http://127.0.0.1:5000/products/api/debug/products"
    
    print(f"\nTesting Debug URL with auth: {url}")
    
    try:
        response = session.get(url)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("Response Body (first 500 chars):")
            print(response.text[:500])
            if len(response.text) > 500:
                print("... (truncated)")
                
            # Try to parse as JSON
            try:
                json_data = response.json()
                print("Successfully parsed as JSON:")
                print(json.dumps(json_data, indent=2))
            except json.JSONDecodeError as e:
                print(f"Failed to parse as JSON: {e}")
        else:
            print("Response Body:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Connection Error: Flask app might not be running")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    login_and_test()
    test_debug_endpoint_with_auth()
