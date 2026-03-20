"""
extensions.py — Flask extension singletons.

Instantiated here (without an app) so that any module can import them
without triggering circular imports.  The Flask app calls ``init_app``
on each extension during startup (see app.py).
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()
