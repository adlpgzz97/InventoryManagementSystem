#!/usr/bin/env python3
"""
Test script to call the API endpoint directly
"""

import requests
import json

def test_product_api():
    """Test the product details API endpoint"""
    
    # The specific product ID that's causing the 404 error
    product_id = "7fbadf57-b5de-43b1-a174-6d6cb7c4cd51"
    
    # Test the API endpoint
    url = f"http://127.0.0.1:5000/products/api/{product_id}/details"
    
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("Response Body (first 500 chars):")
            print(response.text[:500])
            if len(response.text) > 500:
                print("... (truncated)")
        else:
            print("Response Body:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Connection Error: Flask app might not be running")
    except Exception as e:
        print(f"Error: {e}")

def test_debug_endpoint():
    """Test the debug endpoint to list all products"""
    
    url = "http://127.0.0.1:5000/products/api/debug/products"
    
    print(f"\nTesting Debug URL: {url}")
    
    try:
        response = requests.get(url)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("Response Body (first 500 chars):")
            print(response.text[:500])
            if len(response.text) > 500:
                print("... (truncated)")
        else:
            print("Response Body:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Connection Error: Flask app might not be running")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_product_api()
    test_debug_endpoint()
