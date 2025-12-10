from datetime import datetime
from .config import db # Import the db instance we created in config

class SurgeryCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    or_suite = db.Column(db.String(50))
    service = db.Column(db.String(50))
    booked_time = db.Column(db.Float)
    
    # Duration fields
    wheels_in = db.Column(db.DateTime, nullable=True)
    wheels_out = db.Column(db.DateTime, nullable=True)
    actual_duration = db.Column(db.Float, nullable=True)
    
    # Metadata
    patient_name = db.Column(db.String(100), nullable=True)
    doctor_name = db.Column(db.String(100), nullable=True) # New field
    is_prediction = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)