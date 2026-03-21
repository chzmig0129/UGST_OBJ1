"""
Application configuration module.

Selects the active config class based on the FLASK_ENV or FLASK_CONFIG
environment variable. Defaults to DevelopmentConfig when neither is set.

Usage in app.py:
    from config import get_config
    app.config.from_object(get_config())
"""

import os


class Config:
    """Base configuration — shared defaults for all environments."""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-key')
    DEBUG = False
    TESTING = False

    # File uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(
        os.environ.get('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024))
    )  # 16 MB default

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False  # Allow UTF-8 characters in JSON responses


class DevelopmentConfig(Config):
    """Local development — SQLite, debug on, safe defaults."""

    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///poligonos.db'
    )


class ProductionConfig(Config):
    """Production — PostgreSQL, no debug, secrets required from env."""

    DEBUG = False

    # Session security
    SESSION_COOKIE_SECURE = os.environ.get('FORCE_HTTPS', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour in seconds

    SECRET_KEY = os.environ.get('SECRET_KEY', '')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://valgeougst:password@localhost:5432/valgeougst',
    )


class TestingConfig(Config):
    """Testing — in-memory SQLite, testing mode on."""

    TESTING = True
    DEBUG = True
    SECRET_KEY = 'test-only-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Disable CSRF and other protections that interfere with tests
    WTF_CSRF_ENABLED = False


# Map of config names to classes
_CONFIG_MAP = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    # Aliases
    'dev': DevelopmentConfig,
    'prod': ProductionConfig,
    'test': TestingConfig,
}


def get_config():
    """Return the appropriate config class based on environment variables.

    Checks FLASK_CONFIG first, then FLASK_ENV. Defaults to DevelopmentConfig.
    """
    env = os.environ.get('FLASK_CONFIG') or os.environ.get('FLASK_ENV', 'development')
    config_class = _CONFIG_MAP.get(env.lower(), DevelopmentConfig)
    return config_class
