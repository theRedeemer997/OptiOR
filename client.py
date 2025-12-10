import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import datetime
import logging
import time

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - FRONTEND - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://127.0.0.1:5000/api"

st.set_page_config(page_title="OR Utilization Manager", layout="wide")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home (Dashboard)", "Predict Duration"])

st.sidebar.markdown("---")
st.sidebar.subheader("Admin Controls")

# --- RETRAIN BUTTON ---
if st.sidebar.button("🔄 Retrain Model"):
    with st.spinner("Training model on latest database records..."):
        try:
            response = requests.post(f"{API_URL}/retrain")
            if response.status_code == 200:
                st.sidebar.success("Model Retrained Successfully! ✅")
                time.sleep(1) 
                st.rerun()    
            else:
                st.sidebar.error("Training Failed. Check backend logs.")
        except requests.exceptions.ConnectionError:
            st.sidebar.error("Cannot connect to backend.")

# --- HOME (Dashboard) ---
if page == "Home (Dashboard)":
    st.title("🏥 Operating Room Dashboard")
    
    # Date Picker
    selected_date = st.date_input("Select Date", datetime.date(2022, 3, 7))
    
    try:
        # Fetch Schedule Data
        response_schedule = requests.get(f"{API_URL}/schedule", params={'date': selected_date})
        if response_schedule.status_code == 200:
            schedule_data = pd.DataFrame(response_schedule.json())
        else:
            schedule_data = pd.DataFrame()

        # 2. Fetch Analytics Data
        response_analytics = requests.get(f"{API_URL}/analytics")
        if response_analytics.status_code == 200:
            analytics_data = response_analytics.json()
        else:
            analytics_data = {}

        # --- LAYOUT START ---
        
        # ROW 1: Table (Left) + Pie Chart (Right)
        row1_col1, row1_col2 = st.columns([3, 2])
        
        with row1_col1:
            st.subheader(f"📅 Schedule for {selected_date}")
            if not schedule_data.empty:
                st.dataframe(schedule_data, height=400, use_container_width=True)
            else:
                st.info("No surgeries scheduled for this date.")
                
        with row1_col2:
            st.subheader("🍰 Case Distribution")
            if analytics_data:
                counts = analytics_data.get('service_counts', {})
                df_counts = pd.DataFrame(list(counts.items()), columns=['Service', 'Count'])
                
                if not df_counts.empty:
                    # PIE CHART
                    fig_pie = px.pie(df_counts, values='Count', names='Service', 
                                     title='Cases by Specialty', hole=0.3)
                    st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---") # Divider line

        # ROW 2: Avg Duration (Left) + Total Workload (Right)
        st.subheader("📈 Operational Metrics")
        row2_col1, row2_col2 = st.columns(2)
        
        with row2_col1:
            st.markdown("**Avg Duration (min) by Specialty**")
            if analytics_data:
                durations = analytics_data.get('avg_duration', {})
                df_dur = pd.DataFrame(list(durations.items()), columns=['Service', 'Avg Duration'])
                
                if not df_dur.empty:
                    fig_bar1 = px.bar(df_dur, x='Service', y='Avg Duration', 
                                      color='Service', text_auto=True)
                    st.plotly_chart(fig_bar1, use_container_width=True)
                    
        with row2_col2:
            st.markdown("**Total Workload (Total Minutes)**")
            # Create a new metric: Count * Avg Duration = Total Minutes occupied
            if analytics_data and not df_counts.empty and not df_dur.empty:
                # Merge the two dataframes
                df_merged = pd.merge(df_counts, df_dur, on='Service')
                df_merged['Total Minutes'] = df_merged['Count'] * df_merged['Avg Duration']
                
                fig_bar2 = px.bar(df_merged, x='Service', y='Total Minutes', 
                                  color='Total Minutes', title="Total OR Time Occupied",
                                  text_auto='.2s') # .2s makes large numbers readable (e.g. 1.2k)
                st.plotly_chart(fig_bar2, use_container_width=True)

    except requests.exceptions.ConnectionError:
        st.error("Could not connect to backend. Please run `python app.py` first.")

# --- PAGE 2: PREDICTION FORM ---
elif page == "Predict Duration":
    st.title("🔮 Predict Surgery Duration")
    st.markdown("Enter the details below to estimate the surgery time.")
    
    with st.form("prediction_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            patient_name = st.text_input("Patient Name")
            surgery_date = st.date_input("Date of Surgery")
            service = st.selectbox("Surgical Specialty", 
                                 ['Orthopedics', 'General', 'Cardiology', 'Urology', 'Thoracic', 
                                  'Neurology', 'Otology', 'Vascular', 'Podiatry', 'Ophthalmology'])
            
            # --- FIX 2: Add Complexity Dropdown ---
            complexity_label = st.selectbox("Procedure Complexity", 
                                          ["Low (Routine)", "Medium (Standard)", "High (Complex)"])
            
            # Map the text label to a number (1, 2, 3) for the backend
            complexity_map = {"Low (Routine)": 1, "Medium (Standard)": 2, "High (Complex)": 3}
            complexity_score = complexity_map[complexity_label]
        
        with col2:
            booked_time = st.number_input("Booked Time (minutes)", min_value=10, value=60)
            or_suite = st.selectbox("Assign OR Suite", [str(i) for i in range(1, 9)])
            
        submit_button = st.form_submit_button("Predict Duration")
        
        if submit_button:
            if patient_name:
                payload = {
                    "patient_name": patient_name,
                    "date": str(surgery_date),
                    "service": service,
                    "booked_time": booked_time,
                    "or_suite": or_suite,
                    "complexity": complexity_score
                }
                
                try:
                    response = requests.post(f"{API_URL}/predict", json=payload)
                    if response.status_code == 200:
                        result = response.json()
                        st.success("Prediction Complete!")
                        st.metric(label="Estimated Duration", value=f"{result['predicted_duration']} min")
                        
                        if result['predicted_duration'] > booked_time:
                            overtime = result['predicted_duration'] - booked_time
                            st.warning(f"⚠️ This surgery is predicted to run overtime by {overtime:.1f} minutes.")
                        else:
                            st.info("✅ This surgery is predicted to finish within the booked time.")
                    else:
                        st.error("Error getting prediction.")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter a patient name.")