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

def start_flask_app():
    """Start Flask application in a separate process"""
    try:
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
        
        # Create window without JavaScript API to avoid evaluation issues
        window = webview.create_window(
            'Inventory Management System',
            login_url,
            width=1200,
            height=800,
            resizable=True,
            text_select=True,
            # Don't use js_api to avoid JavaScript evaluation issues
            frameless=False,
            easy_drag=True,
            fullscreen=False
        )
        
        # Give the window a moment to initialize
        print("* Waiting for PyWebView window to initialize...")
        time.sleep(1)
        
        # Window is ready for use
        print("* PyWebView window created successfully")
        

        
        # Start webview
        print("* Starting desktop application...")
        print(f"* Flask URL: {flask_url}")
        print(f"* Debug mode: {config.DEBUG}")
        print("* Note: Press F12 in the desktop app to open developer tools (if supported)")
        
        try:
            # Start webview with debug mode
            webview.start(debug=config.DEBUG)
        except Exception as e:
            print(f"* PyWebView error: {e}")
            print("* This might be due to:")
            print("* 1. Flask backend not fully initialized")
            print("* 2. PyWebView compatibility issues")
            print("* 3. System resources or permissions")
            
            # Try to get Flask status
            try:
                response = requests.get(flask_url, timeout=5)
                print(f"* Flask status check: {response.status_code}")
            except Exception as flask_check_error:
                print(f"* Flask connectivity check failed: {flask_check_error}")
            
            input("Press Enter to exit...")
            return
        
        # Cleanup
        if flask_process and flask_process.poll() is None:
            flask_process.terminate()
            flask_process.wait()
            print("* Flask backend stopped")
        
    except KeyboardInterrupt:
        print("\n* Application interrupted by user")
    except Exception as e:
        print(f"* Unexpected error: {e}")
        input("Press Enter to exit...")
    finally:
        print("* Application shutdown complete")

if __name__ == '__main__':
    main()
