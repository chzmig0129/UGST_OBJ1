from flask_sqlalchemy import SQLAlchemy

# Create a database instance without initializing it
db = SQLAlchemy()

def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
    
    # Create all tables in the database if they don't exist
    with app.app_context():
        db.create_all() 