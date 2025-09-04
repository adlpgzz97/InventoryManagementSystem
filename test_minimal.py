#!/usr/bin/env python3
"""
Minimal test script to check Flask app functionality
"""

import requests
import sys
import time

def test_minimal():
    """Test minimal Flask functionality"""
    print("Testing minimal Flask functionality...")
    
    # Test 1: Check if server responds at all
    try:
        print("Testing basic connectivity...")
        response = requests.get('http://localhost:5001/', timeout=5)
        print(f"✓ Root route: {response.status_code}")
        return True
    except requests.exceptions.Timeout:
        print("✗ Root route timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Connection refused")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    print("=== Minimal Flask Test ===\n")
    
    # Test basic functionality
    if test_minimal():
        print("\n✓ Basic test passed!")
    else:
        print("\n✗ Basic test failed!")
        sys.exit(1)
