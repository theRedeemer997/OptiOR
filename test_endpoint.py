import requests

try:
    resp = requests.post('http://127.0.0.1:5000/api/predict_average', json={'service': 'Cardiology'})
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Error: {e}")
