"""
scripts/init_db.py — Database initialization script.

Creates all SQLAlchemy tables defined in app.py within the application context.
Works with both SQLite (development) and PostgreSQL (production) based on the
active configuration (controlled by FLASK_ENV / FLASK_CONFIG env vars).

Usage:
    python scripts/init_db.py
    FLASK_ENV=production python scripts/init_db.py
"""

import sys
import os

# Ensure the project root is on the Python path so that app.py and its
# dependencies can be imported regardless of where this script is invoked from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app, db  # noqa: E402 — must come after sys.path adjustment


def init_db():
    """Create all database tables within the Flask application context."""
    with app.app_context():
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')

        # Determine the database backend for informational output.
        if db_uri.startswith('sqlite'):
            db_type = 'SQLite'
            db_location = db_uri.replace('sqlite:///', '')
        elif db_uri.startswith('postgresql'):
            db_type = 'PostgreSQL'
            db_location = db_uri
        else:
            db_type = 'Unknown'
            db_location = db_uri

        print(f"[init_db] Using {db_type} database: {db_location}")
        print("[init_db] Creating tables (existing tables will not be modified)...")

        db.create_all()

        print("[init_db] All tables created successfully.")


if __name__ == '__main__':
    init_db()
