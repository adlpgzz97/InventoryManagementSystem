# Configuration Management - Inventory Management System

## Overview
The Inventory Management System now uses a centralized, secure configuration management system that eliminates hardcoded credentials and provides environment-specific configuration.

## 🚀 Quick Start

### 1. Automatic Setup (Recommended)
Run the setup script to create your configuration:
```bash
python setup_environment.py
```

This script will:
- Prompt for database credentials
- Generate a secure secret key
- Create a `.env` file with your configuration
- Validate the setup

### 2. Manual Setup
Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=inventory_db
DB_USER=postgres
DB_PASSWORD=your_password_here

# Application Configuration
APP_HOST=127.0.0.1
APP_PORT=5001

# Security Configuration
SECRET_KEY=your_secret_key_here

# Environment Settings
FLASK_ENV=development
FLASK_DEBUG=True
```

## 🔧 Configuration Options

### Database Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL server hostname |
| `DB_PORT` | `5432` | PostgreSQL server port |
| `DB_NAME` | `inventory_db` | Database name |
| `DB_USER` | `postgres` | Database username |
| `DB_PASSWORD` | **Required** | Database password |

### Application Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `127.0.0.1` | Flask application host |
| `APP_PORT` | `5001` | Flask application port |
| `FLASK_ENV` | `development` | Flask environment |
| `FLASK_DEBUG` | `True` | Enable debug mode |

### Security Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | **Required** | Flask secret key for sessions |
| `SESSION_COOKIE_SECURE` | `False` | Secure cookies (HTTPS only) |
| `PERMANENT_SESSION_LIFETIME` | `3600` | Session lifetime in seconds |

### Logging Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `app.log` | Log file path |

## 🌍 Environment-Specific Configuration

The system automatically detects the environment and applies appropriate settings:

### Development Environment
- Debug mode enabled
- Detailed logging
- Non-secure session cookies
- Local database connections

### Production Environment
- Debug mode disabled
- Warning-level logging
- Secure session cookies
- Production database settings

### Testing Environment
- Debug mode enabled
- Test database configuration
- Detailed logging for debugging

## 🔍 Configuration Validation

### Manual Validation
Run the configuration validator:
```bash
cd backend
python validate_config.py
```

### What It Checks
- Required environment variables are set
- Database connection can be established
- Configuration values are valid
- Security warnings for development settings

## 🛡️ Security Features

### Credential Protection
- **No hardcoded passwords** in source code
- Environment variables for sensitive data
- Secure password input during setup
- Configuration validation prevents insecure defaults

### Session Security
- Configurable session lifetime
- Secure cookie settings for production
- CSRF protection enabled
- XSS protection headers

## 📁 File Structure

```
InventoryAppDev/
├── .env                          # Your local configuration (create this)
├── env.template                  # Template showing all variables
├── setup_environment.py         # Interactive setup script
├── backend/
│   ├── config.py                # Centralized configuration system
│   ├── validate_config.py       # Configuration validator
│   └── utils/
│       └── database.py          # Database utilities using config
└── main.py                      # Desktop app using config
```

## 🔄 Migration from Old System

### Before (Hardcoded)
```python
# OLD - Hardcoded credentials
db_config = {
    'host': 'localhost',
    'port': '5432',
    'database': 'inventory_db',
    'user': 'postgres',
    'password': 'TatUtil97=='  # ❌ Security risk!
}
```

### After (Environment-based)
```python
# NEW - Secure configuration
from config import config

db_config = config.DB_CONFIG  # ✅ Secure and flexible
```

## 🚨 Troubleshooting

### Common Issues

#### 1. "DB_PASSWORD environment variable is required"
**Solution**: Set the `DB_PASSWORD` environment variable or run `setup_environment.py`

#### 2. "Database connection failed"
**Solution**: 
- Check PostgreSQL is running
- Verify database credentials
- Ensure database exists

#### 3. "Configuration validation failed"
**Solution**: 
- Check all required environment variables
- Run `python backend/validate_config.py` for details

### Debug Mode
Enable debug mode to see detailed error messages:
```bash
export FLASK_DEBUG=True
```

## 📚 API Reference

### Configuration Object
```python
from config import config

# Access configuration values
db_host = config.DB_HOST
db_port = config.DB_PORT
debug_mode = config.DEBUG

# Get database configuration
db_config = config.DB_CONFIG

# Check environment
is_prod = config.is_production()
```

### Environment Variables
```python
import os

# Set configuration
os.environ['DB_PASSWORD'] = 'new_password'
os.environ['FLASK_DEBUG'] = 'False'

# Reload configuration
from config import get_config
config = get_config()
```

## 🔮 Future Enhancements

- [ ] Configuration hot-reloading
- [ ] Encrypted configuration files
- [ ] Configuration backup/restore
- [ ] Configuration migration tools
- [ ] Configuration monitoring dashboard

## 📞 Support

If you encounter configuration issues:

1. Check the troubleshooting section above
2. Run the configuration validator
3. Review your `.env` file
4. Check the application logs

For additional help, refer to the main project documentation or create an issue in the project repository.
