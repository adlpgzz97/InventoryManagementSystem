# Inventory Management System

A comprehensive web-based inventory management system built with Flask, PostgreSQL, and modern web technologies.

## Features

- **Product Management**: Add, edit, delete, and track products with SKU, barcode, and batch tracking
- **Stock Management**: Real-time stock levels with warehouse and location tracking
- **Warehouse Management**: Multi-warehouse support with aisle/bin location system
- **User Management**: Role-based access control (Admin, Manager, Worker)
- **Advanced Search & Filtering**: Search across products, stock, and locations
- **Sorting & Pagination**: Sortable columns with configurable pagination
- **Bulk Operations**: Select multiple items for bulk delete/export operations
- **CSV Export**: Export data to CSV format for external analysis
- **Barcode Scanning**: Support for barcode scanning (when hardware is available)
- **Responsive Design**: Mobile-friendly interface using Bootstrap 5

## Technology Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Bootstrap 5
- **Icons**: Font Awesome
- **Authentication**: Flask-Login with session management

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <your-github-repo-url>
   cd InventoryAppDev
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**
   - Create a new PostgreSQL database
   - Run the configuration setup script:
   ```bash
   python setup_environment.py
   ```
   This will create a `.env` file with your database credentials.

5. **Initialize the database**
   ```bash
   python backend/app.py
   ```
   The application will automatically create tables and seed initial data.

6. **Run the application**
   ```bash
   # Option 1: Desktop application
   python main.py
   
   # Option 2: Web application only
   python backend/app.py
   ```

7. **Access the application**
   - Desktop app will open automatically
   - Or open your browser and go to `http://127.0.0.1:5001`
   - Login with default credentials:
     - **Admin**: admin / admin123
     - **Manager**: manager / manager123
     - **Worker**: worker / worker123

## Project Structure

```
InventoryAppDev/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── models.py           # Database models
│   ├── views/              # HTML templates
│   │   ├── base.html       # Base template
│   │   ├── products.html   # Products page
│   │   ├── stock.html      # Stock management page
│   │   └── warehouses.html # Warehouse management page
│   └── static/             # Static files (CSS, JS, images)
├── venv/                   # Virtual environment
├── .gitignore             # Git ignore file
├── README.md              # This file
└── requirements.txt       # Python dependencies
```

## Usage

### Product Management
- Add new products with SKU, name, description, dimensions, weight, and barcode
- Enable batch tracking for products that require it
- Search and filter products by category, name, or SKU
- Sort products by any column
- Export product data to CSV

### Stock Management
- Track stock levels across multiple warehouses
- Monitor available, reserved, and total quantities
- Set up warehouse locations with aisle/bin system
- Filter stock by warehouse, status (in stock, low stock, out of stock)
- Bulk operations for stock management

### User Roles

#### Admin
- Full access to all features
- Can manage users and system settings
- Can delete products and stock items

#### Manager
- Can add, edit, and view all data
- Cannot delete items (safety feature)
- Can export data and manage inventory

#### Worker
- Read-only access to most features
- Can view products and stock levels
- Limited to basic search and filtering

## API Endpoints

The application provides RESTful API endpoints for programmatic access:

- `GET /api/products` - List all products
- `GET /api/stock` - List all stock items
- `GET /api/warehouses` - List all warehouses
- `POST /api/products` - Create new product
- `PUT /api/products/<id>` - Update product
- `DELETE /api/products/<id>` - Delete product

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on GitHub or contact the development team.

## Changelog

### Version 1.0.0
- Initial release
- Basic CRUD operations for products, stock, and warehouses
- User authentication and role-based access control
- Search, filtering, and sorting functionality
- CSV export capabilities
- Responsive web interface
