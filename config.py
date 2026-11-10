import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '')
    APP_ENV = os.getenv('APP_ENV', 'development')
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL') or os.getenv('RENDER_EXTERNAL_URL', '')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = int(os.getenv('DB_PORT', '3306'))
    DB_NAME = os.getenv('DB_NAME', 'northwind')
    DB_USER = os.getenv('DB_USER', 'northwind_app')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_SSL_CA = os.getenv('DB_SSL_CA') or None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    MAX_CONTENT_LENGTH = 128 * 1024
