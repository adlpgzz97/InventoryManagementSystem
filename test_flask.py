#!/usr/bin/env python3
"""
Simple test script to run Flask app directly
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

# Change to backend directory
os.chdir(str(backend_dir))

print("=" * 50)
print("TESTING FLASK APP DIRECTLY")
print("=" * 50)
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path[0]}")

try:
    # Import and run the Flask app
    from app import app
    print("* Flask app imported successfully")
    print("* Starting Flask server...")
    app.run(debug=False, host='127.0.0.1', port=5000)
except Exception as e:
    print(f"* Error: {e}")
    import traceback
    traceback.print_exc()
