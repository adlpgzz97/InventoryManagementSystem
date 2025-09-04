#!/usr/bin/env python3
"""
CLI tool for managing database migrations
"""

import argparse
import sys
import os
from typing import Optional

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from backend.utils.migrations.migration_manager import MigrationManager


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Database Migration Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show migration status
  python cli.py status
  
  # Apply all pending migrations
  python cli.py migrate
  
  # Apply migrations up to specific version
  python cli.py migrate --target 005
  
  # Rollback specific migration
  python cli.py rollback --version 005
  
  # Rollback all migrations
  python cli.py rollback --all
  
  # Create new migration
  python cli.py create --version 006 --description "Add user preferences table"
  
  # Create schema migration
  python cli.py create --version 007 --description "Add indexes" --type schema
  
  # Create data migration
  python cli.py create --version 008 --description "Seed initial data" --type data
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Apply pending migrations')
    migrate_parser.add_argument(
        '--target', '-t',
        help='Target migration version (apply up to this version)'
    )
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migrations')
    rollback_group = rollback_parser.add_mutually_exclusive_group(required=True)
    rollback_group.add_argument(
        '--version', '-v',
        help='Rollback specific migration version'
    )
    rollback_group.add_argument(
        '--all', '-a',
        action='store_true',
        help='Rollback all migrations'
    )
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument(
        '--version', '-v',
        required=True,
        help='Migration version (e.g., 001, 002)'
    )
    create_parser.add_argument(
        '--description', '-d',
        required=True,
        help='Migration description'
    )
    create_parser.add_argument(
        '--type', '-t',
        choices=['basic', 'schema', 'data'],
        default='basic',
        help='Migration type (default: basic)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Initialize migration manager
        migration_manager = MigrationManager()
        
        if args.command == 'status':
            return show_status(migration_manager)
        elif args.command == 'migrate':
            return migrate(migration_manager, args.target)
        elif args.command == 'rollback':
            if args.all:
                return rollback_all(migration_manager)
            else:
                return rollback_version(migration_manager, args.version)
        elif args.command == 'create':
            return create_migration(migration_manager, args.version, args.description, args.type)
        else:
            print(f"Unknown command: {args.command}")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        return 1


def show_status(migration_manager: MigrationManager) -> int:
    """Show migration status"""
    try:
        status = migration_manager.get_migration_status()
        
        print("Migration Status")
        print("=" * 50)
        print(f"Applied migrations: {status['applied_count']}")
        print(f"Pending migrations: {status['pending_count']}")
        print(f"Total migrations: {status['total_count']}")
        print()
        
        if status['applied_migrations']:
            print("Applied Migrations:")
            print("-" * 30)
            for migration in status['applied_migrations']:
                print(f"  {migration['version']}: {migration['description']}")
                print(f"    Applied: {migration['applied_at']}")
                print(f"    Status: {migration['status']}")
                if migration['execution_time_ms']:
                    print(f"    Duration: {migration['execution_time_ms']}ms")
                print()
        
        if status['pending_migrations']:
            print("Pending Migrations:")
            print("-" * 30)
            for migration in status['pending_migrations']:
                print(f"  {migration['version']}: {migration['description']}")
                print(f"    File: {migration['filename']}")
                print()
        
        if status['last_applied']:
            print(f"Last applied: {status['last_applied']['version']} - {status['last_applied']['description']}")
        
        if status['next_pending']:
            print(f"Next pending: {status['next_pending']['version']} - {status['next_pending']['description']}")
        
        return 0
        
    except Exception as e:
        print(f"Failed to get migration status: {e}")
        return 1


def migrate(migration_manager: MigrationManager, target_version: Optional[str] = None) -> int:
    """Apply migrations"""
    try:
        if target_version:
            print(f"Applying migrations up to version {target_version}...")
        else:
            print("Applying all pending migrations...")
        
        success = migration_manager.migrate(target_version)
        
        if success:
            print("Migration completed successfully!")
            return 0
        else:
            print("Migration failed!")
            return 1
            
    except Exception as e:
        print(f"Migration failed: {e}")
        return 1


def rollback_version(migration_manager: MigrationManager, version: str) -> int:
    """Rollback specific migration version"""
    try:
        print(f"Rolling back migration {version}...")
        
        success = migration_manager.rollback_migration(version)
        
        if success:
            print(f"Migration {version} rolled back successfully!")
            return 0
        else:
            print(f"Failed to rollback migration {version}!")
            return 1
            
    except Exception as e:
        print(f"Rollback failed: {e}")
        return 1


def rollback_all(migration_manager: MigrationManager) -> int:
    """Rollback all migrations"""
    try:
        print("Rolling back all migrations...")
        
        success = migration_manager.rollback_all()
        
        if success:
            print("All migrations rolled back successfully!")
            return 0
        else:
            print("Failed to rollback all migrations!")
            return 1
            
    except Exception as e:
        print(f"Rollback failed: {e}")
        return 1


def create_migration(migration_manager: MigrationManager, version: str, description: str, migration_type: str) -> int:
    """Create new migration"""
    try:
        print(f"Creating {migration_type} migration {version}: {description}")
        
        filepath = migration_manager.create_migration(version, description, migration_type)
        
        print(f"Migration file created: {filepath}")
        print("Please edit the file to implement your migration logic.")
        return 0
        
    except Exception as e:
        print(f"Failed to create migration: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
