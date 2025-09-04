# Inventory Management System Launcher (PowerShell)

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Inventory Management System" -ForegroundColor Cyan  
Write-Host "PostgreSQL Database Mode" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-Not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    Write-Host "Then run: venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "Then run: pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host "See POSTGRESQL_SETUP.md for database setup" -ForegroundColor Cyan
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment and run desktop application
& "venv\Scripts\Activate.ps1"
Write-Host "Ensure PostgreSQL is running before launching" -ForegroundColor Yellow
Write-Host "Starting Desktop Application..." -ForegroundColor Green
python main.py

Read-Host "Press Enter to exit"