"""
Simple Inventory Management App Launcher
Fast startup with minimal checks for local development
"""

import webview
import threading
import time
import sys
import os
import subprocess
import requests
from pathlib import Path

# Import configuration
from backend.config import config

def start_flask_app():
    """Start Flask application quickly"""
    try:
        print(f"* Starting Flask on {config.APP_HOST}:{config.APP_PORT}")
        
        # Start Flask app
        venv_python = Path(__file__).parent / 'venv' / 'Scripts' / 'python.exe'
        python_executable = str(venv_python) if venv_python.exists() else sys.executable
        
        flask_process = subprocess.Popen(
            [python_executable, '-m', 'backend.app'],
            cwd=str(Path(__file__).parent),
            stdout=None,  # Don't capture stdout - let it display
            stderr=None,  # Don't capture stderr - let it display
            text=True
        )
        
        # Quick startup check - only wait 10 seconds max
        flask_url = f'http://{config.APP_HOST}:{config.APP_PORT}'
        
        print(f"* Checking Flask startup at {flask_url}")
        
        for attempt in range(10):  # Reduced from 60 to 10
            try:
                if flask_process.poll() is not None:
                    print(f"* Flask failed to start (exit code: {flask_process.returncode})")
                    return None, None
                
                response = requests.get(flask_url, timeout=1)
                if response.status_code in [200, 302, 404, 500]:
                    print(f"* Flask started successfully on {flask_url}")
                    
                    # Test a few key endpoints to ensure they're working
                    try:
                        test_endpoints = ['/api/health', '/auth/login']
                        for endpoint in test_endpoints:
                            test_response = requests.get(f"{flask_url}{endpoint}", timeout=2)
                            print(f"* Test endpoint {endpoint}: {test_response.status_code}")
                    except Exception as e:
                        print(f"* Warning: Endpoint test failed: {e}")
                    
                    return flask_process, flask_url
                    
            except requests.exceptions.ConnectionError:
                print(f"* Attempt {attempt + 1}: Connection refused, waiting...")
                pass
            except Exception as e:
                print(f"* Error: {e}")
            
            time.sleep(0.5)  # Reduced from 1 second to 0.5 seconds
        
        print("* Flask startup timeout")
        return None, None
        
    except Exception as e:
        print(f"* Error starting Flask: {e}")
        return None, None

def main():
    """Main entry point - simplified and fast"""
    print("* Starting Inventory Management System...")
    
    try:
        # Start Flask backend
        flask_process, flask_url = start_flask_app()
        if not flask_process:
            print("* Failed to start Flask")
            input("Press Enter to exit...")
            return
        
        # Create window immediately - no extensive checks
        import time
        cache_buster = int(time.time())
        login_url = f'{flask_url}/auth/login?cb={cache_buster}'
        print(f"* Opening login page: {login_url}")
        
        # Create PyWebView window with minimal configuration
        window = webview.create_window(
            'Inventory Management System',
            login_url,
            width=1200,
            height=800,
            resizable=True
        )
        
        print("* Starting desktop app...")
        
        # Start webview
        webview.start(debug=False)  # Disable debug for faster startup
        
        # Cleanup
        if flask_process and flask_process.poll() is None:
            flask_process.terminate()
            flask_process.wait(timeout=5)
        
    except KeyboardInterrupt:
        print("\n* Application interrupted")
    except Exception as e:
        print(f"* Error: {e}")
        input("Press Enter to exit...")
    finally:
        print("* Application closed")

if __name__ == '__main__':
    main()
