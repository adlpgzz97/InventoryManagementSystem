@echo off
echo ===================================
echo Inventory Management System
echo PostgreSQL Database Mode
echo ===================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then run: venv\Scripts\activate.bat
    echo Then run: pip install -r requirements.txt
    echo See POSTGRESQL_SETUP.md for database setup
    pause
    exit /b 1
)

REM Activate virtual environment and run desktop application
call venv\Scripts\activate.bat
echo Ensure PostgreSQL is running before launching
echo Starting Desktop Application...
python main.py

pause