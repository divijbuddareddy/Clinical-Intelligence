import pytest
import os
import sys
import io
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from config import Config
from models.database import db
from models.patient_model import Patient
from models.document_model import Document
from services.document_processor import DocumentProcessor

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        # Create test patient
        patient = Patient(
            patient_code="PT-9999",
            display_name="Test Patient",
            date_of_birth="1980-01-01",
            primary_condition="Hypertension"
        )
        db.session.add(patient)
        db.session.commit()

        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_document_text_cleaner():
    raw = "Patient has\n\n\n\nsevere   migraines.\x00"
    cleaned = DocumentProcessor.clean_text(raw)
    assert "\x00" not in cleaned
    assert "severe migraines." in cleaned
    assert "   " not in cleaned

def test_document_chunker():
    pages_data = [
        {
            "page_number": 1,
            "text": "CHIEF COMPLAINT: Patient reports frequent headache. " * 30,
            "section": "Chief Complaint"
        }
    ]
    chunks = DocumentProcessor.chunk_document(pages_data, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    assert chunks[0]["page_number"] == 1
    assert "chunk_index" in chunks[0]

def test_upload_document_endpoint(client):
    patient = Patient.query.first()
    data = {
        "file": (io.BytesIO(b"CHIEF COMPLAINT: Patient presenting with acute headache.\nPAST HISTORY: None."), "test_note.txt"),
        "document_type": "CLINICAL_NOTE",
        "auto_process": "false"
    }
    res = client.post(
        f"/api/patients/{patient.id}/documents",
        data=data,
        content_type="multipart/form-data"
    )
    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["document"]["original_filename"] == "test_note.txt"
    assert json_data["document"]["status"] == "UPLOADED"
