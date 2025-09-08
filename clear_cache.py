"""
Clear PyWebView cache and cookies
"""

import os
import shutil
import tempfile
from pathlib import Path

def clear_pywebview_cache():
    """Clear PyWebView cache and cookies"""
    print("Clearing PyWebView cache and cookies...")
    
    try:
        # Get the user's temp directory
        temp_dir = Path(tempfile.gettempdir())
        
        # Common PyWebView cache locations
        cache_locations = [
            temp_dir / "pywebview",
            temp_dir / "webview",
            Path.home() / "AppData" / "Local" / "Temp" / "pywebview",
            Path.home() / "AppData" / "Local" / "Temp" / "webview",
            Path.home() / ".cache" / "pywebview",
            Path.home() / ".cache" / "webview"
        ]
        
        cleared_count = 0
        for cache_path in cache_locations:
            if cache_path.exists():
                try:
                    shutil.rmtree(cache_path)
                    print(f"✅ Cleared: {cache_path}")
                    cleared_count += 1
                except Exception as e:
                    print(f"⚠️  Could not clear {cache_path}: {e}")
        
        if cleared_count == 0:
            print("ℹ️  No PyWebView cache directories found")
        else:
            print(f"✅ Cleared {cleared_count} cache directories")
        
        # Also clear any session files in the project
        project_session_files = [
            "session.db",
            "flask_session",
            ".flask_session"
        ]
        
        for session_file in project_session_files:
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    print(f"✅ Removed session file: {session_file}")
                except Exception as e:
                    print(f"⚠️  Could not remove {session_file}: {e}")
        
        print("\n✅ Cache clearing completed!")
        print("You can now restart the app with a clean cache.")
        
    except Exception as e:
        print(f"❌ Error clearing cache: {e}")

if __name__ == "__main__":
    clear_pywebview_cache()
