"""
Inventory Management App - Desktop Launcher
Simplified pywebview wrapper for Flask application
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

def cleanup_existing_processes():
    """Clean up any existing Python processes that might be using our port"""
    try:
        import psutil
        
        # Find Python processes that might be running Flask
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python.exe':
                    cmdline = proc.info['cmdline']
                    if cmdline and any('backend.app' in arg for arg in cmdline):
                        print(f"* Found existing Flask process (PID: {proc.info['pid']}), terminating...")
                        proc.terminate()
                        proc.wait(timeout=5)
                        print(f"* Existing Flask process terminated")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
    except ImportError:
        print("* psutil not available, skipping process cleanup")
        # Fallback: try to kill Python processes (less precise)
        try:
            import subprocess
            result = subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("* Cleaned up existing Python processes")
        except Exception as e:
            print(f"* Process cleanup failed: {e}")

def check_port_availability(host, port):
    """Check if the port is available for binding"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            if result == 0:
                print(f"* Warning: Port {port} is already in use")
                return False
            else:
                print(f"* Port {port} is available")
                return True
    except Exception as e:
        print(f"* Port check failed: {e}")
        return False

def start_flask_app():
    """Start Flask application in a separate process"""
    try:
        # Clean up any existing processes first
        cleanup_existing_processes()
        
        # Check if our port is available
        if not check_port_availability(config.APP_HOST, config.APP_PORT):
            print(f"* Waiting for port {config.APP_PORT} to become available...")
            time.sleep(3)
            if not check_port_availability(config.APP_HOST, config.APP_PORT):
                print(f"* Error: Port {config.APP_PORT} is still in use after cleanup")
                return None, None
        
        # Change to backend directory - main.py is in root, so backend is just 'backend'
        backend_dir = Path(__file__).parent / 'backend'
        
        # Check PostgreSQL connection using centralized configuration
        try:
            import psycopg2
            test_conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            test_conn.close()
            app_file = 'app.py'
            print("* PostgreSQL connection successful")
        except ImportError:
            print("* PostgreSQL driver (psycopg2) not available")
            print("* Please install with: pip install psycopg2-binary")
            return None, None
        except Exception as e:
            print(f"* PostgreSQL connection failed: {e}")
            print("* Please check your database configuration and ensure PostgreSQL is running")
            print("* See POSTGRESQL_SETUP.md for database setup instructions")
            return None, None
        
        # Start Flask app with virtual environment Python
        venv_python = Path(__file__).parent / 'venv' / 'Scripts' / 'python.exe'
        if venv_python.exists():
            python_executable = str(venv_python)
            print(f"* Using virtual environment Python: {python_executable}")
        else:
            python_executable = sys.executable
            print(f"* Using system Python: {python_executable}")
        
        flask_process = subprocess.Popen(
            [python_executable, '-m', 'backend.app'],
            cwd=str(Path(__file__).parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Wait for Flask to start on configured port
        flask_url = f'http://{config.APP_HOST}:{config.APP_PORT}'
        max_attempts = 60  # Increased timeout to 60 seconds
        
        print(f"* Waiting for Flask to start on {flask_url}...")
        
        for attempt in range(max_attempts):
            try:
                # Check if process is still running
                if flask_process.poll() is not None:
                    print(f"* Flask process terminated unexpectedly (exit code: {flask_process.returncode})")
                    # Get any error output
                    try:
                        output, _ = flask_process.communicate(timeout=1)
                        if output:
                            print(f"* Flask output: {output}")
                    except:
                        pass
                    return None, None
                
                # Try to connect to Flask
                response = requests.get(flask_url, timeout=2)
                if response.status_code in [200, 302, 404, 500]:  # Flask is responding (including errors)
                    print(f"* Flask application started successfully on {flask_url} (attempt {attempt + 1}/{max_attempts})")
                    # Give Flask a moment to fully initialize
                    time.sleep(2)
                    return flask_process, flask_url
                else:
                    print(f"* Flask responding with status {response.status_code}, waiting...")
            except requests.exceptions.ConnectionError:
                if attempt % 5 == 0:  # Show progress every 5 attempts
                    print(f"* Waiting for Flask to start... (attempt {attempt + 1}/{max_attempts})")
            except Exception as e:
                print(f"* Error checking Flask status: {e}")
            
            time.sleep(1)
        
        print("* Failed to start Flask application within timeout")
        # Try to get Flask output for debugging
        try:
            flask_process.terminate()
            output, _ = flask_process.communicate(timeout=5)
            if output:
                print(f"* Flask startup output: {output}")
        except:
            pass
        return None, None
        
    except Exception as e:
        print(f"* Error starting Flask: {e}")
        return None, None

def main():
    """Main entry point"""
    print("* Starting Inventory Management Desktop Application...")
    print("* PostgreSQL Database Mode")
    
    try:
        # Check if Flask backend exists
        backend_app = Path(__file__).parent / 'backend' / 'app.py'
        if not backend_app.exists():
            print("* Error: Flask backend not found. Please ensure backend/app.py exists.")
            input("Press Enter to exit...")
            return
        
        # Display configuration information
        print(f"* Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
        print(f"* Flask will run on: {config.APP_HOST}:{config.APP_PORT}")
        
        # Start Flask backend
        flask_process, flask_url = start_flask_app()
        if not flask_process:
            print("* Failed to start Flask backend")
            input("Press Enter to exit...")
            return
        
        # Additional health check before starting PyWebView
        print("* Performing final health check...")
        try:
            health_response = requests.get(f'{flask_url}/api/health', timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"* Health check passed: {health_data.get('message', 'OK')}")
            else:
                print(f"* Health check failed with status: {health_response.status_code}")
                print("* Proceeding anyway, but PyWebView may fail...")
        except Exception as e:
            print(f"* Health check failed: {e}")
            print("* Proceeding anyway, but PyWebView may fail...")
        
        # Create desktop window
        print("* Creating desktop window...")
        # Start directly at the login page to avoid redirect loops
        login_url = f'{flask_url}/auth/login'
        print(f"* Starting at login page: {login_url}")
        
        # Test if the login page is accessible before creating PyWebView
        print("* Testing login page accessibility...")
        try:
            test_response = requests.get(login_url, timeout=5)
            if test_response.status_code == 200:
                print(f"* ✅ Login page accessible (Status: {test_response.status_code})")
            else:
                print(f"* ⚠️  Login page returned status: {test_response.status_code}")
        except Exception as e:
            print(f"* ❌ Login page test failed: {e}")
            print("* Cannot proceed with PyWebView if login page is not accessible")
            input("Press Enter to exit...")
            return
        
        # Create window with Windows-compatible configuration
        print("* Creating PyWebView window with Windows-optimized settings...")
        try:
            window = webview.create_window(
                'Inventory Management System',
                login_url,
                width=1200,
                height=800,
                resizable=True,
                text_select=True,
                frameless=False,
                easy_drag=False,  # Disable easy_drag on Windows
                fullscreen=False,
                confirm_close=False,
                background_color='#FFFFFF',
                # Windows-specific options
                min_size=(800, 600)
            )
            print("* PyWebView window created successfully")
        except Exception as e:
            print(f"* Failed to create PyWebView window: {e}")
            print("* Trying minimal Windows configuration...")
            
            # Try minimal configuration for Windows
            try:
                window = webview.create_window(
                    'Inventory Management System',
                    login_url,
                    width=1200,
                    height=800
                )
                print("* Minimal PyWebView window created")
            except Exception as e2:
                print(f"* Minimal configuration also failed: {e2}")
                print("* Cannot create PyWebView window")
                input("Press Enter to exit...")
                return
        
        # Set custom User-Agent for desktop app identification
        try:
            # This will help Flask identify desktop app requests
            window.set_title('Inventory Management System - Desktop App')
            print("* Custom title set for desktop app identification")
        except Exception as e:
            print(f"* Could not set custom title: {e}")
        
        print("* Desktop app window created successfully")
        
        # Give the window a moment to initialize
        print("* Waiting for PyWebView window to initialize...")
        time.sleep(2)  # Increased wait time for Windows
        
        # Verify window was created successfully
        if not window:
            print("* Error: PyWebView window is None")
            input("Press Enter to exit...")
            return
            
        print("* PyWebView window created successfully")
        print("* Window properties:")
        print(f"   - Title: {getattr(window, 'title', 'N/A')}")
        print(f"   - URL: {getattr(window, 'url', 'N/A')}")
        print(f"   - Width: {getattr(window, 'width', 'N/A')}")
        print(f"   - Height: {getattr(window, 'height', 'N/A')}")
        

        
        # Start webview
        print("* Starting desktop application...")
        print(f"* Flask URL: {flask_url}")
        print(f"* Debug mode: {config.DEBUG}")
        print("* Note: Press F12 in the desktop app to open developer tools (if supported)")
        
        try:
            # Start webview with debug mode and better error handling
            print("* Starting PyWebView...")
            webview.start(debug=config.DEBUG)
            print("* PyWebView started successfully")
        except Exception as e:
            print(f"* PyWebView error: {e}")
            print("* This might be due to:")
            print("* 1. Flask backend not fully initialized")
            print("* 2. PyWebView compatibility issues")
            print("* 3. System resources or permissions")
            print("* 4. URL loading issues")
            
            # Try to get Flask status
            try:
                response = requests.get(flask_url, timeout=5)
                print(f"* Flask status check: {response.status_code}")
                
                # Test the specific login URL
                login_response = requests.get(login_url, timeout=5)
                print(f"* Login URL status: {login_response.status_code}")
                if login_response.status_code == 200:
                    print("* Login page is accessible")
                else:
                    print(f"* Login page issue: {login_response.status_code}")
                    
            except Exception as flask_check_error:
                print(f"* Flask connectivity check failed: {flask_check_error}")
            
            print("* Press Enter to exit...")
            input()
            return
        
        # Cleanup
        if flask_process and flask_process.poll() is None:
            print("* Shutting down Flask backend...")
            flask_process.terminate()
            try:
                flask_process.wait(timeout=10)
                print("* Flask backend stopped gracefully")
            except subprocess.TimeoutExpired:
                print("* Force killing Flask backend...")
                flask_process.kill()
                flask_process.wait()
                print("* Flask backend force stopped")
        
    except KeyboardInterrupt:
        print("\n* Application interrupted by user")
    except Exception as e:
        print(f"* Unexpected error: {e}")
        input("Press Enter to exit...")
    finally:
        print("* Application shutdown complete")

if __name__ == '__main__':
    main()
