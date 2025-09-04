#!/usr/bin/env python3
"""
Debug configuration values
"""

from backend.config import config

print("Configuration values:")
print(f"APP_HOST: {config.APP_HOST}")
print(f"APP_PORT: {config.APP_PORT}")
print(f"DB_HOST: {config.DB_HOST}")
print(f"DB_PORT: {config.DB_PORT}")
print(f"DB_NAME: {config.DB_NAME}")
print(f"DB_USER: {config.DB_USER}")
print(f"DEBUG: {config.DEBUG}")
print(f"SECRET_KEY: {config.SECRET_KEY[:20]}...")
