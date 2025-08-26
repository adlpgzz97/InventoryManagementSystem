# Inventory Management App - Setup Guide

This guide will help you resolve the inconsistencies in the codebase and get the application running properly.

## Issues Found and Fixed

### 1. **Missing Dependencies** ✅ FIXED
- **Issue**: `psycopg2-binary` was commented out in `requirements.txt`
- **Fix**: Uncommented the PostgreSQL driver dependency
- **Action**: Run `pip install -r requirements.txt`

### 2. **Database Schema Mismatch** ✅ FIXED
- **Issue**: Missing batch tracking columns and audit trail table
- **Fix**: Created migration script `db/migration_batch_tracking.sql`
- **Action**: Run the migration script

### 3. **Multiple App Files** ⚠️ NEEDS DECISION
- **Issue**: Three different app files with different implementations
- **Files**: `app.py`, `app_fixed.py`, `app_demo.py`
- **Recommendation**: Use `app.py` (most complete) or `app_fixed.py` (simpler)

## Step-by-Step Setup

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Git (for cloning)

### 1. Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies (now includes psycopg2-binary)
pip install -r requirements.txt
```

### 2. Setup PostgreSQL Database
```bash
# Create database
createdb -U postgres inventory_db

# Run initial schema
psql -U postgres -d inventory_db -f db/schema.sql

# Run migration to add missing features
psql -U postgres -d inventory_db -f db/migration_batch_tracking.sql
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:
```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=inventory_db
DB_USER=postgres
DB_PASSWORD=your_password_here

# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# PostgREST Configuration (optional)
POSTGREST_URL=http://localhost:3000
```

### 4. Test Setup
```bash
# Run the test script to verify everything works
python test_app_connection.py
```

### 5. Run the Application

#### Option A: Use the main app (recommended)
```bash
cd backend
python app.py
```

#### Option B: Use the simplified app
```bash
cd backend
python app_fixed.py
```

#### Option C: Desktop application
```bash
python desktop/main.py
```

## Database Schema Overview

After running the migration, your database will have:

### Core Tables
- `users` - Application users with role-based access
- `products` - Product catalog with batch tracking support
- `warehouses` - Warehouse locations
- `locations` - Specific storage locations within warehouses
- `stock_items` - Inventory with batch tracking and expiry dates
- `stock_transactions` - Audit trail for all stock movements

### Key Features Added
- **Batch Tracking**: Products can be marked as batch-tracked
- **Expiry Dates**: Support for product expiration dates
- **Audit Trail**: Complete history of stock movements
- **Smart Stock Receiving**: Automatically handles batch vs non-batch products

## Default Login Credentials

- **Admin**: username: `admin`, password: `admin123`
- **Manager**: username: `manager`, password: `manager123`
- **Worker**: username: `worker`, password: `worker123`

## Troubleshooting

### Common Issues

#### 1. Import Error: No module named 'psycopg2'
```bash
# Solution: Install the PostgreSQL driver
pip install psycopg2-binary
```

#### 2. Database Connection Failed
- Check if PostgreSQL is running
- Verify database exists: `createdb -U postgres inventory_db`
- Check credentials in `.env` file
- Ensure database user has proper permissions

#### 3. Missing Tables
```bash
# Run the schema setup
psql -U postgres -d inventory_db -f db/schema.sql
psql -U postgres -d inventory_db -f db/migration_batch_tracking.sql
```

#### 4. Template Errors
- Ensure `backend/views/` directory exists
- Check that all template files are present
- Verify Flask app is configured with correct template folder

### Testing Your Setup

Run the test script to verify everything is working:
```bash
python test_app_connection.py
```

This will check:
- All required packages are installed
- Database connection works
- Required tables exist
- Flask app can be imported

## Application Structure

```
InventoryAppDev/
├── backend/                 # Flask application
│   ├── app.py              # Main Flask app (recommended)
│   ├── app_fixed.py        # Simplified version
│   ├── views/              # Jinja2 templates
│   └── ...
├── db/                     # Database files
│   ├── schema.sql         # Initial schema
│   ├── migration_batch_tracking.sql  # Migration script
│   └── ...
├── desktop/                # Desktop application
├── requirements.txt       # Python dependencies
├── test_app_connection.py # Setup verification script
└── SETUP_GUIDE.md        # This file
```

## Next Steps

After successful setup:

1. **Explore the Application**: Login and navigate through the interface
2. **Add Sample Data**: Use the "Add" buttons to create products, warehouses, and stock
3. **Test Features**: Try batch tracking, stock movements, and reporting
4. **Customize**: Modify templates and add new features as needed

## Support

If you encounter issues:
1. Run `python test_app_connection.py` to diagnose problems
2. Check the troubleshooting section above
3. Review the error messages in the application logs
4. Ensure all prerequisites are met

The application should now work correctly with all inconsistencies resolved!
