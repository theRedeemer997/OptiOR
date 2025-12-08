import logging
from flask import Flask, jsonify, request
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from datetime import datetime

from database.config import db, init_db
from database.schema import SurgeryCase

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - BACKEND - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

server = Flask(__name__)

# --- Initialize Database ---
init_db(server)

# Global model variable
model = None

# --- Migration Function (CSV -> DB) ---
# In app.py

def seed_database_logic():
    """Reads CSV and populates DB if empty"""
    try:
        # Check if DB is empty
        if SurgeryCase.query.first() is None:
            logger.info("Database is empty. Starting migration from CSV...")
            df = pd.read_csv('./data/2022_Q1_OR_Utilization.csv')
            
            # --- FIX STARTS HERE ---
            # 1. Parse Dates directly (Do NOT concatenate Date column)
            # The CSV format is likely "MM/DD/YY HH:MM AM" which pandas handles automatically
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Wheels In'] = pd.to_datetime(df['Wheels In'], errors='coerce')
            df['Wheels Out'] = pd.to_datetime(df['Wheels Out'], errors='coerce')
            # -----------------------
            
            # 2. Calculate Duration
            df['Actual Duration'] = (df['Wheels Out'] - df['Wheels In']).dt.total_seconds() / 60
            
            # 3. Filter valid rows
            df_clean = df.dropna(subset=['Actual Duration', 'Service', 'Booked Time (min)'])
            
            # Prepare for DB
            db_df = pd.DataFrame({
                'date': df_clean['Date'],
                'or_suite': df_clean['OR Suite'].astype(str),
                'service': df_clean['Service'],
                'booked_time': df_clean['Booked Time (min)'],
                'wheels_in': df_clean['Wheels In'],
                'wheels_out': df_clean['Wheels Out'],
                'actual_duration': df_clean['Actual Duration'],
                'patient_name': None,
                'is_prediction': False,
                'timestamp': datetime.now() # Updated from utcnow() to avoid deprecation warning
            })
            
            db_df.to_sql('surgery_case', con=db.engine, if_exists='append', index=False)
            
            count = len(db_df)
            logger.info(f"Migration Complete. {count} records inserted.")
            return True, f"Seeding Complete. {count} records added."
        else:
            logger.info("Database already contains data.")
            return False, "Database is not empty. Clear it first if you want to re-seed."
    except Exception as e:
        logger.error(f"Migration Failed: {e}")
        return False, str(e)

# --- Training Function ---
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

        # looks for booked_time and day_of_week and if there is some null vlaue anywhere it inserts the median
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
        logger.warning("Database empty on startup. Please call /api/seed to load data.")
        logger.info(f"Calling seed function")
        success, message = seed_database_logic()
        if success:logger.info(f"message : {message}")
        else:
            logger.info(f"message : {message}")

# --- 4. API Endpoints ---

# --- NEW: Seed Endpoint ---
@server.route('/api/seed', methods=['POST'])
def seed_db():
    success, message = seed_database_logic()
    if success:
        # Auto-train after seeding
        global model
        model = train_model()
        return jsonify({"message": message, "status": "success"}), 200
    else:
        return jsonify({"message": message, "status": "error"}), 400

# --- NEW: Clear Endpoint ---
@server.route('/api/clear', methods=['DELETE'])
def clear_db():
    try:
        num_rows = db.session.query(SurgeryCase).delete()
        db.session.commit()
        logger.info(f"Database cleared. Deleted {num_rows} rows.")
        
        # Reset model since no data exists
        global model
        model = None
        
        return jsonify({"message": f"Database cleared. {num_rows} records deleted.", "status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e), "status": "error"}), 500

@server.route('/api/schedule', methods=['GET'])
def get_schedule():
    date_str = request.args.get('date', '2022-03-07')
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        # Use the imported Model to query
        cases = SurgeryCase.query.filter(db.func.date(SurgeryCase.date) == date_obj.date()).all()
        
        results = []
        for case in cases:
            results.append({
                'OR Suite': case.or_suite,
                'Service': case.service,
                'Booked Time (min)': case.booked_time,
                'OR Schedule': case.wheels_in.strftime('%H:%M') if case.wheels_in else "TBD",
                'Actual Duration': case.actual_duration
            })
        results.sort(key=lambda x: x['OR Schedule'])
        return jsonify(results)
    except Exception as e:
        logger.error(f"Schedule Error: {e}")
        return jsonify([]), 500

@server.route('/api/analytics', methods=['GET'])
def get_analytics():
    try:
        df = pd.read_sql("SELECT service, actual_duration FROM surgery_case WHERE actual_duration IS NOT NULL", db.engine)
        if df.empty:
             return jsonify({'service_counts': {}, 'avg_duration': {}})
             
        service_counts = df['service'].value_counts().to_dict()
        avg_duration = df.groupby('service')['actual_duration'].mean().round(1).to_dict()
        return jsonify({'service_counts': service_counts, 'avg_duration': avg_duration})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@server.route('/api/predict', methods=['POST'])
def predict():
    global model
    data = request.json
    if model is None:
        return jsonify({"error": "Model not trained. Please Seed DB first."}), 500

    try:
        # Predict
        input_data = pd.DataFrame([{
            'service': data['service'],
            'booked_time': float(data['booked_time']),
            'day_of_week': pd.to_datetime(data['date']).dayofweek
        }])
        
        prediction = model.predict(input_data)[0]
        
        # Save using the imported Model
        new_case = SurgeryCase(
            date=pd.to_datetime(data['date']),
            service=data['service'],
            booked_time=float(data['booked_time']),
            patient_name=data['patient_name'],
            actual_duration=None,
            is_prediction=True
        )
        db.session.add(new_case)
        db.session.commit()
        
        logger.info(f"New case saved. Prediction: {prediction:.1f}")
        return jsonify({'predicted_duration': round(prediction, 1), 'patient': data['patient_name']})
    except Exception as e:
        logger.error(f"Prediction Error: {e}")
        return jsonify({"error": str(e)}), 500

@server.route('/api/retrain', methods=['POST'])
def retrain():
    global model
    logger.info("Retraining request received.")
    try:
        new_model = train_model()
        if new_model:
            model = new_model
            return jsonify({"message": "Model retrained successfully", "status": "success"})
        else:
            return jsonify({"message": "Training failed (No data?)", "status": "error"}), 500
    except Exception as e:
        return jsonify({"message": str(e), "status": "error"}), 500

if __name__ == '__main__':
    server.run(debug=True, port=5000)