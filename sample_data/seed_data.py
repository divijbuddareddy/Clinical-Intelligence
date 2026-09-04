import os
import sys
import shutil
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from config import Config
from models.database import db
from models.user_model import User, UserRole
from models.patient_model import Patient
from models.document_model import Document, DocumentChunk
from models.report_model import Report
from models.audit_model import AuditLog
from sample_data.generate_all_sample_reports import generate_all_samples

def reset_and_seed_database():
    app = create_app()
    with app.app_context():
        print("Cleaning previous database tables and vector files...")
        
        # Drop and recreate tables for a clean slate
        db.drop_all()
        db.create_all()

        # Clean runtime directories
        for folder in [Config.UPLOAD_FOLDER, Config.VECTOR_STORE_FOLDER, Config.EXPORT_FOLDER]:
            if folder.exists():
                for item in folder.glob("*"):
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    except Exception as e:
                        print(f"Clean warning: {e}")

        # 1. Seed Demo Users
        users_data = [
            {
                "name": "Dr. Sarah Jenkins, MD",
                "email": "doctor@brainsight.ai",
                "password": "doctor123",
                "role": UserRole.DOCTOR,
                "specialty": "Neurology & Clinical Neurophysiology"
            },
            {
                "name": "Nurse Marcus Reed, RN",
                "email": "staff@brainsight.ai",
                "password": "staff123",
                "role": UserRole.CLINICAL_STAFF,
                "specialty": "Clinical Care Coordinator"
            },
            {
                "name": "Alex Taylor (Admin)",
                "email": "admin@brainsight.ai",
                "password": "admin123",
                "role": UserRole.ADMIN,
                "specialty": "Health Informatics"
            }
        ]

        for u in users_data:
            user = User(
                name=u["name"],
                email=u["email"],
                role=u["role"],
                specialty=u["specialty"]
            )
            user.set_password(u["password"])
            db.session.add(user)
            print(f"Created user: {u['email']} ({u['role']})")
        db.session.commit()

        # 2. Generate Sample PDFs in sample_data/ folder (ready for user to upload)
        print("\nGenerating sample clinical report files in sample_data/ for user uploading...")
        generate_all_samples(BASE_DIR)

        # 3. Create Clean Patient Profiles (NO pre-uploaded or pre-indexed documents)
        patients_definitions = [
            {
                "patient_code": "PT-8942",
                "display_name": "Eleanor Vance",
                "date_of_birth": "1970-04-12",
                "gender": "Female",
                "primary_condition": "Refractory Temporal Lobe Epilepsy",
                "attending_physician": "Dr. Sarah Jenkins, MD"
            },
            {
                "patient_code": "PT-3108",
                "display_name": "Robert Langdon",
                "date_of_birth": "1962-09-18",
                "gender": "Male",
                "primary_condition": "Acute Left MCA Ischemic Stroke",
                "attending_physician": "Dr. Sarah Jenkins, MD"
            },
            {
                "patient_code": "PT-7721",
                "display_name": "Sophia Chen",
                "date_of_birth": "1981-11-25",
                "gender": "Female",
                "primary_condition": "Relapsing-Remitting Multiple Sclerosis",
                "attending_physician": "Dr. Sarah Jenkins, MD"
            },
            {
                "patient_code": "PT-5519",
                "display_name": "Marcus Thorne",
                "date_of_birth": "1978-06-03",
                "gender": "Male",
                "primary_condition": "Traumatic Subdural Hematoma Craniotomy",
                "attending_physician": "Dr. Sarah Jenkins, MD"
            },
            {
                "patient_code": "PT-9204",
                "display_name": "Clara Oswald",
                "date_of_birth": "1958-03-14",
                "gender": "Female",
                "primary_condition": "Parkinson's Disease (DBS Candidate)",
                "attending_physician": "Dr. Sarah Jenkins, MD"
            }
        ]

        for p_meta in patients_definitions:
            pat = Patient(**p_meta)
            db.session.add(pat)
            db.session.commit()
            print(f"Created clean patient profile: {pat.display_name} ({pat.patient_code})")

        print("\nSUCCESS: Database reset cleanly!")
        print("Sample PDF files are ready in 'sample_data/' folder for user uploading.")
        print("All patient profiles are clean with 0 pre-attached documents or reports.")

if __name__ == "__main__":
    reset_and_seed_database()
