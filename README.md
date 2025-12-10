# OptiOR - Operating Room Analytics & Prediction

OptiOR is a web-based application designed to help hospitals analyze operating room (OR) utilization and predict surgery durations. It provides an interactive dashboard for visualizing historical data and a machine learning tool to estimate future case times.

The application consists of a **Flask** backend that serves a REST API and a **Next.js (React)** frontend that provides a modern, interactive user interface.

---

## Features

- **Interactive Schedule**: View daily and monthly OR schedules using a full-featured calendar.
- **Drag-and-Drop Scheduling**: Update surgery times and assignments by dragging events on the calendar.
- **Surgery Duration Prediction**: Uses a machine learning model to predict the duration of a new surgery based on its characteristics.
- **Analytics Dashboard**: Visualize key metrics like case distribution, OR suite utilization, and average surgery durations.
- **Dynamic Data Seeding**: Initializes the database with a full year of realistic, procedurally generated data.
- **RESTful API**: A clean backend API to manage cases, doctors, and predictions.

---

## Project Layout

```
OptiOR/
├── web-app/               # Next.js/React Frontend
│   ├── app/
│   ├── components/
│   ├── package.json
│   └── ...
├── database/              # DB configuration and SQLAlchemy schema
│   ├── config.py
│   └── schema.py
├── models/                # Stores the trained machine learning model
│   └── OptiOR.joblib
├── server_new.py          # Flask backend server
├── start_app.py           # Main script to run the application
├── seed_2025.py           # Script to seed the database
├── requirements.txt       # Python project dependencies
└── README.md
```

---

## Running OptiOR

Follow these steps to get the application running locally.

### 1. Install Dependencies

The project requires both Python and Node.js dependencies.

**A. Python Dependencies**

First, install the required Python packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

**B. Frontend Dependencies**

Navigate to the `web-app` directory and install the Node.js packages:

```bash
cd web-app
npm install
cd ..
```

### 2. Seed the Database (One-Time Step)

Before using the application for the first time, you must populate the database with sample data. Run the following command from the project root:

```bash
python seed_2025.py
```

This will generate and load a full year of data into the SQLite database (`database/or_database.db`).

### 3. Start the Application

The easiest way to run the application is to use the provided `start_app.py` script. This will launch both the backend and frontend servers concurrently.

```bash
python start_app.py
```

The script will output the URLs for both services:

-   **Backend API**: `http://127.0.0.1:5000`
-   **Frontend App**: `http://localhost:3000`

You can now open `http://localhost:3000` in your browser to use the application.

---

## How to Use the Application

-   **Dashboard**: Open the application to view the main dashboard and analytics.
-   **Schedule**: Navigate to the "Schedule" page to see the interactive calendar.
-   **Add a Case**: Click on a date in the calendar to open a modal and schedule a new surgery. The system will provide a predicted duration.
-   **Update a Case**: Drag and drop existing surgeries to reschedule them.

---

## API Endpoints

The Flask server (`server_new.py`) provides the following API endpoints:

-   `GET /api/cases`: Retrieves all scheduled cases.
-   `POST /api/cases`: Creates a new surgery case.
-   `PUT /api/cases/<int:case_id>`: Updates an existing case.
-   `DELETE /api/cases/<int:case_id>`: Deletes a case.
-   `GET /api/doctors`: Returns a list of available doctors grouped by specialty.
-   `POST /api/predict_suggestion`: Provides a duration prediction for a new, unsaved case.
-   `POST /api/predict_average`: Provides a duration prediction based on historical averages for a given service.
-   `GET /api/analytics`: Retrieves aggregate data for dashboard charts (e.g., case counts, average durations).
-   `GET /api/analytics/status`: Retrieves high-level stats for the dashboard header.

## Screenshots
<img width="1915" height="911" alt="image" src="https://github.com/user-attachments/assets/2ad16682-37d2-4be4-8d35-e39bef5a8c69" />
<img width="1913" height="914" alt="image" src="https://github.com/user-attachments/assets/cf7db046-b6dc-41fc-951b-a2b1d72ca5be" />
<img width="1895" height="913" alt="image" src="https://github.com/user-attachments/assets/d18d3a1c-9129-4295-9239-6812244aa01b" />
<img width="1919" height="909" alt="image" src="https://github.com/user-attachments/assets/1ba901f9-dafe-4463-93a3-c06dfbb9e746" />
<img width="1919" height="900" alt="image" src="https://github.com/user-attachments/assets/7f07907d-3018-4139-81d1-8c959c761e3c" />




