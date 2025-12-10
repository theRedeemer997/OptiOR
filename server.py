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

def seed_database_logic():
    """Reads CSV and populates DB if empty"""
    try:
        # Check if DB is empty
        if SurgeryCase.query.first() is None:
            logger.info("Database is empty. Starting migration from CSV...")
            df = pd.read_csv('./data/2022_Q1_OR_Utilization.csv')
            
            # --- FIX STARTS HERE ---
            # 1. Parse Dates directly
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
                'timestamp': datetime.now()
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

def train_model():
    logger.info("Loading training data from Database...")
    try:
        # 1. Fetch data
        query = "SELECT * FROM surgery_case WHERE actual_duration IS NOT NULL"
        df = pd.read_sql(query, db.engine)
        
        if df.empty:
            logger.warning("No training data found in DB.")
            return None

        # --- Remove Outliers ---
        # Only keep surgeries between 15 mins and 8 hours (480 mins)
        # This prevents 1-minute test entries or 24-hour errors from confusing the AI.
        df = df[(df['actual_duration'] > 15) & (df['actual_duration'] < 480)]

        # --- Feature Engineering ---
        df['date'] = pd.to_datetime(df['date'])
        df['day_of_week'] = df['date'].dt.dayofweek
        
        # Convert 'or_suite' to string so the model treats it as a category (Room "1" vs Room "2")
        # instead of a number (where Room 2 is "double" Room 1).
        df['or_suite'] = df['or_suite'].astype(str) 

        # We define the features we want to learn from
        features = ['service', 'booked_time', 'day_of_week', 'or_suite']
        
        # If 'complexity' exists in your DB (from Fix 2), add it. Otherwise, ignore it.
        if 'complexity' in df.columns:
            features.append('complexity')

        X = df[features]
        y = df['actual_duration']

        
        # We need to tell the model which columns are Categories (Text) and which are Numbers.
        categorical_cols = ['service', 'or_suite']
        numerical_cols = ['booked_time', 'day_of_week']
        
        if 'complexity' in features:
            numerical_cols.append('complexity')

        preprocessor = ColumnTransformer(
            transformers=[
                ('num', SimpleImputer(strategy='median'), numerical_cols),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
            ])

        # n_estimators=200: Uses more "decision trees" for better consensus.
        # max_depth=10: Prevents the model from memorizing noise (overfitting).
        new_model = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('model', RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42))
        ])
        
        new_model.fit(X, y)
        logger.info(f"Model trained successfully on {len(df)} records.")
        return new_model
    except Exception as e:
        logger.error(f"Training Failed: {e}")
        return None

# --- API Endpoints ---
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

# --- Clear Endpoint ---
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
        # Prepare input for the model
        # We default 'complexity' to 2 (Medium) if the user didn't send it, 
        # or if the model isn't trained to use it yet.
        input_row = {
            'service': data['service'],
            'booked_time': float(data['booked_time']),
            'day_of_week': pd.to_datetime(data['date']).dayofweek,
            'or_suite': str(data['or_suite']),
            'complexity': data.get('complexity', 2)
        }
        
        input_data = pd.DataFrame([input_row])
        
        # Make Prediction
        prediction = model.predict(input_data)[0]
        predicted_val = round(prediction, 1)

        # Update the Database Object
        # NOTE: You must update your 'SurgeryCase' schema in database/schema.py 
        # to include a 'complexity' column for this to save permanently.
        new_case = SurgeryCase(
            date=pd.to_datetime(data['date']),
            service=data['service'],
            booked_time=float(data['booked_time']),
            patient_name=data['patient_name'],
            or_suite=data['or_suite'],
            actual_duration=predicted_val, # Using the predicted value as discussed
            is_prediction=True
        )
        db.session.add(new_case)
        db.session.commit()
        
        logger.info(f"New case saved. Prediction: {predicted_val}")
        return jsonify({'predicted_duration': predicted_val, 'patient': data['patient_name']})
    except Exception as e:
        logger.error(f"Prediction Error: {e}")
        # Fallback: If the model crashes because it wasn't trained on 'complexity' yet,
        # we try predicting WITHOUT complexity.
        try:
            logger.info("Attempting fallback prediction without complexity...")
            del input_row['complexity']
            input_data = pd.DataFrame([input_row])
            prediction = model.predict(input_data)[0]
            return jsonify({'predicted_duration': round(prediction, 1), 'patient': data['patient_name']})
        except:
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