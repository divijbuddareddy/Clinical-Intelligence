import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app
from sample_data.seed_data import reset_and_seed_database as seed_database

if __name__ == "__main__":
    # Check if database exists, if not seed initial demo data
    db_file = Path(__file__).resolve().parent / "clinical_platform.db"
    if not db_file.exists():
        print("[Startup] Initializing and seeding database with demo patient and document records...")
        seed_database()

    app = create_app()
    print("=" * 65)
    print(" CLINICAL WORKFLOW INTELLIGENCE PLATFORM")
    print(" Server running on: http://127.0.0.1:5000")
    print(" Demo Credentials:")
    print("   Doctor: doctor@brainsight.ai / doctor123")
    print("   Staff:  staff@brainsight.ai  / staff123")
    print("   Admin:  admin@brainsight.ai  / admin123")
    print("=" * 65)
    app.run(host="127.0.0.1", port=5000, debug=False)
