"""
scripts/create_admin.py — Admin user creation script.

Creates a new admin user in the database.  The password is hashed via
flask-bcrypt before storage — it is never saved in plaintext.

Usage:
    python scripts/create_admin.py --username admin --email admin@example.com --password secretpass

Exit codes:
    0 — user created successfully
    1 — user already exists (duplicate username or email)
    2 — unexpected error
"""

import sys
import os
import argparse

# Ensure the project root is on the Python path so that app.py and its
# dependencies can be imported regardless of where this script is invoked from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app, db, User  # noqa: E402 — must come after sys.path adjustment


def parse_args():
    parser = argparse.ArgumentParser(
        description='Create an admin user in the UGST application database.'
    )
    parser.add_argument(
        '--username',
        required=True,
        help='Username for the new admin account (must be unique).',
    )
    parser.add_argument(
        '--email',
        required=True,
        help='Email address for the new admin account (must be unique).',
    )
    parser.add_argument(
        '--password',
        required=True,
        help='Plain-text password; will be hashed before storage.',
    )
    return parser.parse_args()


def create_admin(username: str, email: str, password: str) -> None:
    """Create an admin user within the Flask application context."""
    with app.app_context():
        # Check for existing user with the same username or email.
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing is not None:
            if existing.username == username:
                print(
                    f"[create_admin] ERROR: A user with username '{username}' already exists.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"[create_admin] ERROR: A user with email '{email}' already exists.",
                    file=sys.stderr,
                )
            sys.exit(1)

        # Build the new admin user and hash the password.
        user = User(
            username=username,
            email=email,
            is_admin=True,
            is_active=True,
        )
        user.set_password(password)  # hashes via flask-bcrypt

        db.session.add(user)
        db.session.commit()

        print(
            f"[create_admin] Admin user '{username}' ({email}) created successfully."
        )


if __name__ == '__main__':
    args = parse_args()
    try:
        create_admin(
            username=args.username,
            email=args.email,
            password=args.password,
        )
    except Exception as exc:
        print(f"[create_admin] Unexpected error: {exc}", file=sys.stderr)
        sys.exit(2)
