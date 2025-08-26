#!/usr/bin/env python3
"""
Simple web test script - starts Flask and opens browser
"""

import threading
import time
import webbrowser
import sys
import os
from pathlib import Path

def start_flask():
    """Start Flask in a separate thread"""
    import subprocess
    
    # Use the virtual environment Python
    venv_python = Path(__file__).parent / 'venv' / 'Scripts' / 'python.exe'
    backend_dir = Path(__file__).parent / 'backend'
    
    try:
        print("* Starting Flask with virtual environment Python...")
        process = subprocess.Popen(
            [str(venv_python), 'app.py'],
            cwd=str(backend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Read output to monitor Flask startup
        for line in iter(process.stdout.readline, ''):
            print(f"Flask: {line.strip()}")
            if "Running on" in line:
                print("* Flask started successfully!")
                break
        
    except Exception as e:
        print(f"* Flask error: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("=" * 60)
    print("SIMPLE WEB TEST - INVENTORY MANAGEMENT")
    print("=" * 60)
    print("* Starting Flask server in background...")
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Wait for Flask to start
    print("* Waiting for Flask to start...")
    time.sleep(3)
    
    # Open browser
    url = "http://127.0.0.1:5000"
    print(f"* Opening browser to: {url}")
    print("* Login credentials:")
    print("   - admin / admin123")
    print("   - manager / manager123")
    print("   - worker / worker123")
    
    webbrowser.open(url)
    
    print("\n* Flask server is running!")
    print("* Press Ctrl+C to stop the server")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n* Shutting down...")

if __name__ == '__main__':
    main()
