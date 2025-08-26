# PostgreSQL Setup Guide

## Quick Setup for Inventory Management App

### Step 1: Verify PostgreSQL Installation

1. **Open Command Prompt as Administrator**
2. **Check if PostgreSQL is running:**
   ```cmd
   # Check if PostgreSQL service is running
   net start | findstr postgresql
   
   # Or check with services
   services.msc
   ```

### Step 2: Find PostgreSQL Installation

PostgreSQL is usually installed in one of these locations:
- `C:\Program Files\PostgreSQL\[version]\bin\`
- `C:\Program Files (x86)\PostgreSQL\[version]\bin\`

### Step 3: Add PostgreSQL to PATH (Temporary)

Open Command Prompt as Administrator and run:
```cmd
set PATH=%PATH%;C:\Program Files\PostgreSQL\15\bin
```
(Replace `15` with your PostgreSQL version)

### Step 4: Create Database

```cmd
# Method 1: Using createdb
createdb -U postgres inventory_db

# Method 2: Using psql
psql -U postgres -c "CREATE DATABASE inventory_db;"
```

### Step 5: Run Schema

```cmd
psql -U postgres -d inventory_db -f db/schema.sql
```

### Step 6: Test Connection

```cmd
psql -U postgres -d inventory_db -c "SELECT count(*) FROM users;"
```

You should see: `count = 3` (the sample users)

---

## Alternative: Using pgAdmin

1. **Open pgAdmin** (graphical PostgreSQL tool)
2. **Connect to your PostgreSQL server**
3. **Right-click on "Databases" → Create → Database**
4. **Name**: `inventory_db`
5. **Click "Save"**
6. **Right-click on inventory_db → Query Tool**
7. **Copy and paste the contents of `db/schema.sql`**
8. **Click Execute (F5)**

---

## Troubleshooting

### Common Issues:

1. **"psql is not recognized"**
   - PostgreSQL bin directory not in PATH
   - Solution: Add PostgreSQL bin to PATH or use full path

2. **"password authentication failed"**
   - Wrong password for postgres user
   - Solution: Use the password you set during PostgreSQL installation

3. **"connection refused"**
   - PostgreSQL service not running
   - Solution: Start PostgreSQL service

4. **"database already exists"**
   - Database was created previously
   - Solution: Continue with schema step or drop and recreate

### Default Credentials:
- **Username**: `postgres`
- **Password**: Usually set during installation (common: `postgres`, `admin`, or empty)
- **Port**: `5432`
- **Host**: `localhost`

---

## Quick Test

After setup, test with Python:

```python
import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        port='5432',
        database='inventory_db',
        user='postgres',
        password='your_password'  # Replace with your password
    )
    print("PostgreSQL connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
```

---

## Notes

- The application will automatically detect if PostgreSQL is available
- If PostgreSQL is not available, it will fall back to demo mode
- You can always use the demo version with: `python backend/app_demo.py`
