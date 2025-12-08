# database/config.py
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize the extension (but don't bind it to the app yet)
db = SQLAlchemy()

def init_db(app):
    """Configures the database for the provided Flask app"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Go up one level (..) to save the .db file in the main project folder
    db_path = os.path.join(basedir, 'or_database.db')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Bind the db to the app
    db.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()