import random
from datetime import datetime, timedelta
from server_new import server, db, SurgeryCase, DOCTORS_BY_SPECIALTY

def seed_data_2025():
    with server.app_context():
        print("Seeding data for 2025...")
        
        # Clear existing data for 2025 to avoid duplicates if re-run (optional, but safer)
        # db.session.query(SurgeryCase).filter(db.extract('year', SurgeryCase.date) == 2025).delete()
        
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 12, 31)
        current = start_date
        
        or_suites = ['OR-1', 'OR-2', 'OR-3', 'OR-4']
        cases_to_add = []
        
        while current <= end_date:
            # Skip weekends mostly, but maybe some emergencies
            if current.weekday() < 5: # Mon-Fri
                daily_volume = random.randint(3, 8) # 3-8 surgeries per day
            else:
                daily_volume = random.randint(0, 2) # 0-2 on weekends
                
            for _ in range(daily_volume):
                specialty = random.choice(list(DOCTORS_BY_SPECIALTY.keys()))
                doctor = random.choice(DOCTORS_BY_SPECIALTY[specialty])
                or_suite = random.choice(or_suites)
                
                # Random time between 8 AM and 4 PM
                start_hour = random.randint(8, 16) 
                
                # Duration 30 to 180 mins
                duration = random.randint(30, 180)
                
                wheels_in = current.replace(hour=start_hour, minute=random.choice([0, 15, 30, 45]))
                wheels_out = wheels_in + timedelta(minutes=duration)
                
                case = SurgeryCase(
                    date=current,
                    service=specialty,
                    booked_time=float(duration),
                    patient_name=f"Patient-{random.randint(1000, 9999)}",
                    or_suite=or_suite,
                    wheels_in=wheels_in,
                    wheels_out=wheels_out,
                    actual_duration=float(duration),
                    is_prediction=False,
                    doctor_name=doctor
                )
                cases_to_add.append(case)
            
            current += timedelta(days=1)
            
        print(f"Adding {len(cases_to_add)} cases...")
        db.session.add_all(cases_to_add)
        db.session.commit()
        print("Done!")

if __name__ == "__main__":
    seed_data_2025()
