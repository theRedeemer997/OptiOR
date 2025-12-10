import random
from server_new import server, db, SurgeryCase, DOCTORS_BY_SPECIALTY

def backfill_doctors():
    with server.app_context():
        print("Backfilling missing doctor names...")
        
        # Find cases with no doctor
        cases = SurgeryCase.query.filter((SurgeryCase.doctor_name == None) | (SurgeryCase.doctor_name == '')).all()
        
        print(f"Found {len(cases)} cases to update.")
        
        updated_count = 0
        for case in cases:
            specialty = case.service
            
            # Case sensitivity check or fallback
            if specialty not in DOCTORS_BY_SPECIALTY:
                # Try title case if uppercase/lowercase mismatch
                if specialty.title() in DOCTORS_BY_SPECIALTY:
                    specialty = specialty.title()
                else:
                    # Fallback to General if completely unknown
                    specialty = 'General'
            
            doctor = random.choice(DOCTORS_BY_SPECIALTY[specialty])
            case.doctor_name = doctor
            updated_count += 1

        db.session.commit()
        print(f"Successfully updated {updated_count} cases.")

if __name__ == "__main__":
    backfill_doctors()
