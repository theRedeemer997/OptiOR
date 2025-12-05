# backend/server.py

from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import joblib


# returns the absolute path of the folder two levels above
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "2022_Q1_OR_Utilization.csv"
MODEL_PATH = BASE_DIR / "models" / "OptiOR.joblib"

# Define the flask app
app = Flask(__name__)
# For cors error
CORS(app)

# functions that loads the data
def load_data():
    df = pd.read_csv(DATA_PATH, header=None)
    df.columns = [
        'index', 'Encounter ID', 'Date', 'OR Suite', 'Service', 'CPT Code',
       'CPT Description', 'Booked Time (min)', 'OR Schedule', 'Wheels In',
       'Start Time', 'End Time', 'Wheels Out',
    ]

    # convert the date time column to datetime
    for col in ["Date", "Wheels In", "Wheels Out"]:
        df[col] = pd.to_datetime(df[col])

    # get the actual duration in minutes by substracting the "Wheels In" and "Wheels Out"
    df["actual_duration_min"] = (
        df["Wheels Out"] - df["Wheels In"]
    ).dt.total_seconds() / 60

    
    df["overrun_min"] = (
        df["actual_duration_min"] - df["Booked Time (min)"]
    ).clip(lower=0)

    df["day_of_week"] = df["Date"].dt.dayofweek
    df["case_hour"] = df["Wheels In"].dt.hour

    return df

# load the data
df_global = load_data()

# ----- load trained pipeline from notebook -----
artifact = joblib.load(MODEL_PATH)
pipe = artifact["pipeline"]

@app.route("/api/summary", methods=["GET"])
def summary():
    df = df_global

    by_day = df.groupby("case_date", as_index=False).agg(
        used_minutes=("actual_duration_min", "sum"),
        overrun_minutes=("overrun_min", "sum"),
        cases=("encounter_id", "count"),
    )

    block_minutes_per_or = 600  # 10h block per OR
    ors_per_day = (
        df.groupby("case_date")["or_suite"]
        .nunique()
        .reindex(by_day["case_date"].values)
        .values
    )
    total_block_minutes = block_minutes_per_or * ors_per_day
    by_day["utilization_pct"] = (
        by_day["used_minutes"] / total_block_minutes * 100
    )

    return jsonify(
        {
            "avg_utilization_pct": round(by_day["utilization_pct"].mean(), 1),
            "avg_cases_per_day": round(by_day["cases"].mean(), 1),
            "avg_overrun_min": round(df["overrun_min"].
