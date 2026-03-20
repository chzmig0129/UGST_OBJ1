"""
User model for authentication.

This module is imported from app.py *after* db and bcrypt are defined,
so the circular import resolves correctly at runtime.
"""

from flask_login import UserMixin
from datetime import datetime


def get_user_model(db, bcrypt):
    """
    Factory that creates and returns the User SQLAlchemy model.

    Called from app.py after db and bcrypt are initialised:

        from models.user import get_user_model
        User = get_user_model(db, bcrypt)
    """

    class User(UserMixin, db.Model):
        __tablename__ = 'user'

        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(256), nullable=False)
        is_active = db.Column(db.Boolean, default=True, nullable=False)
        is_admin = db.Column(db.Boolean, default=False, nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

        def set_password(self, password):
            """Hash and store the password using flask-bcrypt."""
            self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        def check_password(self, password):
            """Verify a password against the stored hash."""
            return bcrypt.check_password_hash(self.password_hash, password)

        def __repr__(self):
            return f'<User {self.username}>'

    return User
