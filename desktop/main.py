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

def start_flask_app():
    """Start Flask application in a separate process"""
    try:
        # Change to backend directory
        backend_dir = Path(__file__).parent.parent / 'backend'
        
        # Check PostgreSQL connection
        try:
            import psycopg2
            test_conn = psycopg2.connect(
                host='localhost',
                port='5432',
                database='inventory_db',
                user='postgres',
                password='TatUtil97=='
            )
            test_conn.close()
            app_file = 'app.py'
            print("* PostgreSQL connection successful")
        except ImportError:
            print("* PostgreSQL driver (psycopg2) not available")
            print("* Please install with: pip install psycopg2-binary")
            return None
        except Exception as e:
            print(f"* PostgreSQL connection failed: {e}")
            print("* Please check your database configuration and ensure PostgreSQL is running")
            print("* See POSTGRESQL_SETUP.md for database setup instructions")
            return None
        
        # Start Flask app with virtual environment Python
        venv_python = Path(__file__).parent.parent / 'venv' / 'Scripts' / 'python.exe'
        if venv_python.exists():
            python_executable = str(venv_python)
            print(f"* Using virtual environment Python: {python_executable}")
        else:
            python_executable = sys.executable
            print(f"* Using system Python: {python_executable}")
        
        flask_process = subprocess.Popen(
            [python_executable, app_file],
            cwd=str(backend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Wait for Flask to start
        flask_url = 'http://127.0.0.1:5001'
        max_attempts = 30
        output_lines = []
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(flask_url, timeout=1)
                if response.status_code in [200, 302, 404]:  # Flask is responding
                    print("* Flask application started successfully")
                    return flask_process
            except:
                pass
            
            # Check if process has terminated
            if flask_process.poll() is not None:  # Process has terminated
                # Read all remaining output
                try:
                    remaining_output = flask_process.stdout.read()
                    if remaining_output:
                        output_lines.extend(remaining_output.split('\n'))
                except:
                    pass
                break
            
            time.sleep(1)
        
        print("* Failed to start Flask application")
        
        # Show error output
        if output_lines:
            print("* Flask output:")
            for line in output_lines[-10:]:  # Show last 10 lines
                if line.strip():
                    print(f"   {line}")
        
        # Try to get final error output
        try:
            if flask_process.poll() is None:
                flask_process.terminate()
                final_output, _ = flask_process.communicate(timeout=5)
                if final_output:
                    print("* Final Flask error:")
                    for line in final_output.split('\n')[-5:]:  # Show last 5 lines
                        if line.strip():
                            print(f"   {line}")
        except:
            pass
        
        return None
        
    except Exception as e:
        print(f"* Error starting Flask: {e}")
        return None

def main():
    """Main entry point"""
    print("* Starting Inventory Management Desktop Application...")
    print("* PostgreSQL Database Mode")
    
    try:
        # Check if Flask backend exists
        backend_app = Path(__file__).parent.parent / 'backend' / 'app.py'
        if not backend_app.exists():
            print("* Error: Flask backend not found. Please ensure backend/app.py exists.")
            input("Press Enter to exit...")
            return
        
        # Start Flask in background thread
        print("* Starting Flask server...")
        flask_process = start_flask_app()
        
        if not flask_process:
            print("* Failed to start Flask server")
            input("Press Enter to exit...")
            return
        
        # Create and start webview window
        print("* Creating desktop window...")
        print("* Login credentials:")
        print("   - admin / admin123")
        print("   - manager / manager123")
        print("   - worker / worker123")
        
        # Create window without problematic event handlers
        window = webview.create_window(
            title='Inventory Management System',
            url='http://127.0.0.1:5001',
            width=1200,
            height=800,
            min_size=(800, 600),
            resizable=True
        )
        
        # Start webview (blocking call)
        webview.start(debug=False)
        
        # Cleanup when window closes
        print("* Cleaning up...")
        if flask_process:
            flask_process.terminate()
        
    except KeyboardInterrupt:
        print("\n* Application interrupted by user")
        if 'flask_process' in locals() and flask_process:
            flask_process.terminate()
    except Exception as e:
        print(f"* Error starting application: {e}")
        input("Press Enter to exit...")
        if 'flask_process' in locals() and flask_process:
            flask_process.terminate()
    finally:
        print("* Application terminated")

if __name__ == '__main__':
    main()
