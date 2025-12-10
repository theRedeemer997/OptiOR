import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from datetime import datetime
import os

from database.config import db, init_db
from database.schema import SurgeryCase

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - BACKEND_NEW - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

server = Flask(__name__)
CORS(server) # Enable CORS for all routes

# --- Validation Config ---
SPECIALTIES = [
    'Orthopedics', 'General', 'Cardiology', 'Urology', 'Thoracic',
    'Neurology', 'Otology', 'Vascular', 'Podiatry', 'Ophthalmology'
]

DOCTORS_BY_SPECIALTY = {
    'Orthopedics': ['Dr. Bones', 'Dr. Smith', 'Dr. Joint'],
    'General': ['Dr. Lee', 'Dr. White', 'Dr. Grey'],
    'Cardiology': ['Dr. Heart', 'Dr. Pulse', 'Dr. Valve'],
    'Urology': ['Dr. Stream', 'Dr. Stone'],
    'Thoracic': ['Dr. Lung', 'Dr. Ribs'],
    'Neurology': ['Dr. Brain', 'Dr. Nerve'],
    'Otology': ['Dr. Ear', 'Dr. Sound'],
    'Vascular': ['Dr. Vein', 'Dr. Flow'],
    'Podiatry': ['Dr. Foot', 'Dr. Heel'],
    'Ophthalmology': ['Dr. Eye', 'Dr. Sight']
}

# --- Database Extension ---
def check_and_update_schema():
    """Ensure surgery_case table has doctor_name column"""
    with server.app_context():
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('surgery_case')]
        if 'doctor_name' not in columns:
            logger.info("Adding doctor_name column to surgery_case table...")
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE surgery_case ADD COLUMN doctor_name TEXT"))
                conn.commit()
            logger.info("Column added successfully.")

# --- Initialize Database ---
init_db(server)
check_and_update_schema()

# Global model variable
model = None

# --- Training Function (Reused) ---
def train_model():
    logger.info("Loading training data from Database...")
    try:
        # Use pandas read_sql to fetch data
        query = "SELECT * FROM surgery_case WHERE actual_duration IS NOT NULL"
        df = pd.read_sql(query, db.engine)
        
        if df.empty:
            logger.warning("No training data found in DB.")
            return None

        # Feature Eng
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        
        features = ['service', 'booked_time', 'day_of_week']
        X = df[features]
        # target variable
        y = df['actual_duration']

        preprocessor = ColumnTransformer(
            transformers=[
                ('num', SimpleImputer(strategy='median'), ['booked_time', 'day_of_week']),
                ('cat', OneHotEncoder(handle_unknown='ignore'), ['service'])
            ])

        new_model = Pipeline(steps=[('preprocessor', preprocessor),
                                ('model', RandomForestRegressor(n_estimators=100))])
        
        new_model.fit(X, y)
        logger.info(f"Model trained successfully on {len(df)} records.")
        return new_model
    except Exception as e:
        logger.error(f"Training Failed: {e}")
        return None

# --- Startup ---
with server.app_context():
    if SurgeryCase.query.first():
         model = train_model()
    else:
        logger.warning("Database empty. Please seed if needed.")

# --- API Endpoints ---

@server.route('/api/cases', methods=['GET'])
def get_cases():
    try:
        cases = SurgeryCase.query.all()
        results = []
        for case in cases:
            results.append({
                'id': case.id,
                'title': f"{case.service} - {case.patient_name or 'No Name'}",
                'start': case.wheels_in.isoformat() if case.wheels_in else case.date.isoformat(),
                'end': case.wheels_out.isoformat() if case.wheels_out else None,
                'extendedProps': {
                    'or_suite': case.or_suite,
                    'service': case.service,
                    'booked_time': case.booked_time,
                    'actual_duration': case.actual_duration,
                    'patient_name': case.patient_name,
                    'is_prediction': case.is_prediction,
                    'doctor_name': getattr(case, 'doctor_name', None)
                }
            })
        return jsonify(results)
    except Exception as e:
        logger.error(f"Get Cases Error: {e}")
        return jsonify({"error": str(e)}), 500

@server.route('/api/doctors', methods=['GET'])
def get_doctors():
    return jsonify(DOCTORS_BY_SPECIALTY)

@server.route('/api/predict_suggestion', methods=['POST'])
def predict_suggestion():
    global model
    data = request.json
    if model is None:
        # Try training if not loaded
        model = train_model()
        if model is None:
             return jsonify({"error": "Model not trained. Need data."}), 500

    try:
        # Predict
        date_val = pd.to_datetime(data['date'])
        input_data = pd.DataFrame([{
            'service': data['service'],
            'booked_time': float(data['booked_time']),
            'day_of_week': date_val.dayofweek
        }])
        
        prediction = model.predict(input_data)[0]
        predicted_val = round(prediction, 1) # duration in minutes

        return jsonify({'predicted_duration': predicted_val})
    except Exception as e:
        logger.error(f"Prediction Error: {e}")
        return jsonify({"error": str(e)}), 500

@server.route('/api/predict_average', methods=['POST'])
def predict_average():
    data = request.json
    service = data.get('service')
    try:
        # 1. Get Baseline (Average) to seed the model
        avg = db.session.query(db.func.avg(SurgeryCase.actual_duration)).filter(SurgeryCase.service == service).scalar()
        baseline = avg if avg else 60

        # 2. Use the AI Model if available
        if model:
            # We predict specifically for TODAY/Selected Date (passed from front or default today)
            date_str = data.get('date', datetime.now().isoformat())
            date_val = pd.to_datetime(date_str)
            
            input_data = pd.DataFrame([{
                'service': service,
                'booked_time': float(baseline), # Use average as the tentative booking
                'day_of_week': date_val.dayofweek
            }])
            
            prediction = model.predict(input_data)[0]
            result = round(prediction)
        else:
            result = round(baseline)

        return jsonify({'predicted_duration': result, 'source': 'AI Model' if model else 'Historical Avg'})
    except Exception as e:
        logger.error(f"Avg Prediction Error: {e}")
        return jsonify({"predicted_duration": 60}), 200

@server.route('/api/cases', methods=['POST'])
def create_case():
    data = request.json
    try:
        # Expected data: date, service, booked_time, patient_name, or_suite, 
        # wheels_in (start time), wheels_out (calculated from duration), actual_duration (prediction)
        
        date_obj = pd.to_datetime(data['date'])
        wheels_in = pd.to_datetime(data['wheels_in']) 
        wheels_out = pd.to_datetime(data['wheels_out'])
        
        new_case = SurgeryCase(
            date=date_obj,
            service=data['service'],
            booked_time=float(data['booked_time']),
            patient_name=data['patient_name'],
            or_suite=data['or_suite'],
            wheels_in=wheels_in,
            wheels_out=wheels_out,
            actual_duration=float(data['actual_duration']),
            is_prediction=True 
        )
        # Manually set the dynamic column
        if 'doctor_name' in data:
            new_case.doctor_name = data['doctor_name']

        db.session.add(new_case)
        db.session.commit()
        return jsonify({"message": "Case created", "id": new_case.id}), 201
    except Exception as e:
        logger.error(f"Create Case Error: {e}")
        return jsonify({"error": str(e)}), 500

@server.route('/api/cases/<int:case_id>', methods=['PUT'])
def update_case(case_id):
    data = request.json
    case = SurgeryCase.query.get(case_id)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    
    try:
        if 'service' in data: case.service = data['service']
        if 'patient_name' in data: case.patient_name = data['patient_name']
        if 'booked_time' in data: case.booked_time = float(data['booked_time'])
        if 'or_suite' in data: case.or_suite = data['or_suite']
        if 'wheels_in' in data: case.wheels_in = pd.to_datetime(data['wheels_in'])
        if 'wheels_out' in data: case.wheels_out = pd.to_datetime(data['wheels_out'])
        if 'doctor_name' in data: case.doctor_name = data['doctor_name']
        
        db.session.commit()
        return jsonify({"message": "Case updated"}), 200
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@server.route('/api/cases/<int:case_id>', methods=['DELETE'])
def delete_case(case_id):
    case = SurgeryCase.query.get(case_id)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    try:
        db.session.delete(case)
        db.session.commit()
        return jsonify({"message": "Case deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
def filter_query_by_period(query, period):
    now = datetime.now()
    if period == 'day':
        # Filter for today
        return query.filter(db.func.date(SurgeryCase.date) == now.date())
    elif period == 'month':
        # Filter for this month
        return query.filter(db.extract('year', SurgeryCase.date) == now.year,
                            db.extract('month', SurgeryCase.date) == now.month)
    elif period == 'year':
        # Filter for this year
        return query.filter(db.extract('year', SurgeryCase.date) == now.year)
    return query

@server.route('/api/analytics', methods=['GET'])
def get_analytics():
    period = request.args.get('period', 'all')
    try:
        # Build query with filter
        query = SurgeryCase.query.filter(SurgeryCase.actual_duration.isnot(None))
        query = filter_query_by_period(query, period)
        
        # Execute and load into DF
        cases = query.all()
        if not cases:
             return jsonify({'service_counts': {}, 'or_suite_counts': {}, 'avg_duration': {}, 'doctor_counts': {}})
             
        data = [{
            'service': c.service, 
            'or_suite': c.or_suite, 
            'actual_duration': c.actual_duration,
            'doctor_name': getattr(c, 'doctor_name', 'Unknown')
        } for c in cases]
        
        df = pd.DataFrame(data)
        
        # Fill NA doctors
        df['doctor_name'] = df['doctor_name'].fillna('Unassigned')
             
        service_counts = df['service'].value_counts().to_dict()
        or_suite_counts = df['or_suite'].value_counts().to_dict()
        doctor_counts = df['doctor_name'].value_counts().head(10).to_dict() # Top 10
        avg_duration = df.groupby('service')['actual_duration'].mean().round(1).to_dict()
        
        return jsonify({
            'service_counts': service_counts, 
            'or_suite_counts': or_suite_counts,
            'doctor_counts': doctor_counts,
            'avg_duration': avg_duration
        })
    except Exception as e:
        logger.error(f"Analytics Error: {e}")
        return jsonify({"error": str(e)}), 500
        
@server.route('/api/analytics/status', methods=['GET'])
def get_analytics_status():
    period = request.args.get('period', 'all')
    try:
        query = SurgeryCase.query
        query = filter_query_by_period(query, period)
        cases = query.all()
        
        total_cases = len(cases)
        avg_duration = 0
        
        durations = [c.actual_duration for c in cases if c.actual_duration]
        if durations:
             avg_duration = sum(durations) / len(durations)
        
        # Utilization Logic (Mock based on load)
        utilization_status = "Low"
        if total_cases > 5: utilization_status = "Moderate"
        if total_cases > 20: utilization_status = "High"
        
        return jsonify({
            "total_cases": total_cases,
            "avg_duration": round(avg_duration, 1),
            "utilization": utilization_status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    server.run(debug=True, port=5000)
