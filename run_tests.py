#!/usr/bin/env python3
"""
Test Runner for Inventory Management System
Comprehensive testing suite for Phase 5: Testing Implementation
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print('='*60)
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print(f"Error Code: {e.returncode}")
        if e.stdout:
            print("Stdout:")
            print(e.stdout)
        if e.stderr:
            print("Stderr:")
            print(e.stderr)
        return False

def run_unit_tests():
    """Run unit tests only."""
    command = "python -m pytest backend/tests/ -v -m 'unit' --tb=short"
    return run_command(command, "Unit Tests")

def run_integration_tests():
    """Run integration tests only."""
    command = "python -m pytest backend/tests/ -v -m 'integration' --tb=short"
    return run_command(command, "Integration Tests")

def run_all_tests():
    """Run all tests."""
    command = "python -m pytest backend/tests/ -v --tb=short"
    return run_command(command, "All Tests")

def run_test_with_coverage():
    """Run tests with coverage reporting."""
    command = "python -m pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=term-missing"
    return run_command(command, "Tests with Coverage")

def run_specific_test_file(test_file):
    """Run a specific test file."""
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    command = f"python -m pytest {test_file} -v --tb=short"
    return run_command(command, f"Specific Test File: {test_file}")

def run_test_with_markers(marker):
    """Run tests with specific markers."""
    command = f"python -m pytest backend/tests/ -v -m '{marker}' --tb=short"
    return run_command(command, f"Tests with Marker: {marker}")

def run_performance_tests():
    """Run performance tests."""
    command = "python -m pytest backend/tests/ -v -m 'slow' --tb=short"
    return run_command(command, "Performance Tests")

def run_database_tests():
    """Run database-related tests."""
    command = "python -m pytest backend/tests/ -v -m 'database' --tb=short"
    return run_command(command, "Database Tests")

def run_repository_tests():
    """Run repository pattern tests."""
    command = "python -m pytest backend/tests/test_repositories.py -v --tb=short"
    return run_command(command, "Repository Pattern Tests")

def run_migration_tests():
    """Run migration system tests."""
    command = "python -m pytest backend/tests/test_migrations.py -v --tb=short"
    return run_command(command, "Migration System Tests")

def run_query_builder_tests():
    """Run query builder tests."""
    command = "python -m pytest backend/tests/test_query_builder.py -v --tb=short"
    return run_command(command, "Query Builder Tests")

def run_service_tests():
    """Run service layer tests."""
    command = "python -m pytest backend/tests/test_services.py -v --tb=short"
    return run_command(command, "Service Layer Tests")

def run_database_utility_tests():
    """Run database utility tests."""
    command = "python -m pytest backend/tests/test_database.py -v --tb=short"
    return run_command(command, "Database Utility Tests")

def install_test_dependencies():
    """Install test dependencies."""
    command = "pip install -r requirements-test.txt"
    return run_command(command, "Installing Test Dependencies")

def check_test_environment():
    """Check if test environment is properly set up."""
    print("\n🔍 Checking Test Environment...")
    
    # Check if pytest is installed
    try:
        import pytest
        print("✅ pytest is installed")
    except ImportError:
        print("❌ pytest is not installed")
        return False
    
    # Check if test directory exists
    test_dir = Path("backend/tests")
    if test_dir.exists():
        print("✅ Test directory exists")
    else:
        print("❌ Test directory not found")
        return False
    
    # Check if test files exist
    test_files = [
        "backend/tests/test_repositories.py",
        "backend/tests/test_query_builder.py",
        "backend/tests/test_migrations.py",
        "backend/tests/test_database.py",
        "backend/tests/test_services.py"
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"✅ {test_file} exists")
        else:
            print(f"❌ {test_file} not found")
    
    # Check if conftest.py exists
    if Path("backend/tests/conftest.py").exists():
        print("✅ conftest.py exists")
    else:
        print("❌ conftest.py not found")
    
    return True

def generate_test_report():
    """Generate a comprehensive test report."""
    print("\n📊 Generating Test Report...")
    
    # Run tests with coverage
    success = run_test_with_coverage()
    
    if success:
        print("\n📈 Test Report Generated Successfully!")
        print("📁 Coverage report available in: htmlcov/index.html")
        print("📊 Terminal coverage summary displayed above")
    else:
        print("\n❌ Failed to generate test report")
    
    return success

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Inventory Management System Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage reporting")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--database", action="store_true", help="Run database tests")
    parser.add_argument("--repositories", action="store_true", help="Run repository tests")
    parser.add_argument("--migrations", action="store_true", help="Run migration tests")
    parser.add_argument("--query-builder", action="store_true", help="Run query builder tests")
    parser.add_argument("--services", action="store_true", help="Run service tests")
    parser.add_argument("--db-utils", action="store_true", help="Run database utility tests")
    parser.add_argument("--file", type=str, help="Run specific test file")
    parser.add_argument("--marker", type=str, help="Run tests with specific marker")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    parser.add_argument("--check-env", action="store_true", help="Check test environment")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive test report")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    print("🚀 Inventory Management System Test Runner")
    print("Phase 5: Testing Implementation")
    print("="*60)
    
    # Check test environment first
    if args.check_env or not check_test_environment():
        if not check_test_environment():
            print("\n❌ Test environment check failed. Please fix issues before running tests.")
            return 1
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_test_dependencies():
            print("\n❌ Failed to install test dependencies.")
            return 1
    
    success = True
    
    # Run specific test types based on arguments
    if args.unit:
        success &= run_unit_tests()
    
    if args.integration:
        success &= run_integration_tests()
    
    if args.performance:
        success &= run_performance_tests()
    
    if args.database:
        success &= run_database_tests()
    
    if args.repositories:
        success &= run_repository_tests()
    
    if args.migrations:
        success &= run_migration_tests()
    
    if args.query_builder:
        success &= run_query_builder_tests()
    
    if args.services:
        success &= run_service_tests()
    
    if args.db_utils:
        success &= run_database_utility_tests()
    
    if args.file:
        success &= run_specific_test_file(args.file)
    
    if args.marker:
        success &= run_test_with_markers(args.marker)
    
    if args.coverage:
        success &= run_test_with_coverage()
    
    if args.report:
        success &= generate_test_report()
    
    # If no specific tests were requested, run all tests
    if not any([args.unit, args.integration, args.performance, args.database,
                args.repositories, args.migrations, args.query_builder, args.services,
                args.db_utils, args.file, args.marker, args.coverage, args.report]):
        success &= run_all_tests()
    
    # Summary
    print("\n" + "="*60)
    if success:
        print("🎉 All tests completed successfully!")
        print("✅ Phase 5 Testing Implementation: COMPLETE")
    else:
        print("❌ Some tests failed. Please review the output above.")
        print("⚠️  Phase 5 Testing Implementation: INCOMPLETE")
    print("="*60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
