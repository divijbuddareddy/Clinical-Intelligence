import pytest
import os
import sys
import io
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from config import Config
from models.database import db
from models.patient_model import Patient
from models.document_model import Document, DocumentStatus
from models.report_model import Report, ReportStatus
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStoreService
from services.rag_service import RAGService
from services.gemini_service import GeminiService
from services.export_service import ExportService

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

@pytest.fixture
def app_and_client(tmp_path):
    TestConfig.VECTOR_STORE_FOLDER = tmp_path / "test_vector_store"
    TestConfig.UPLOAD_FOLDER = tmp_path / "test_uploads"
    TestConfig.EXPORT_FOLDER = tmp_path / "test_exports"
    
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        
        # Seed test patient
        patient = Patient(
            patient_code="PT-TEST-1",
            display_name="Jane Doe",
            date_of_birth="1985-05-15",
            primary_condition="Focal Epilepsy"
        )
        db.session.add(patient)
        db.session.commit()

        # Seed sample note file
        upload_dir = TestConfig.UPLOAD_FOLDER / f"patient_{patient.id}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        note_path = upload_dir / "clinical_summary.txt"
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(
                "CHIEF COMPLAINT: Recurrent olfactory auras and temporal seizures.\n"
                "MEDICATIONS: Levetiracetam 1500mg BID, Lamotrigine 200mg BID.\n"
                "ALLERGIES: Severe anaphylaxis to Penicillin.\n"
                "LAB FINDINGS: Normal CMP. Video-EEG confirmed left mesial temporal spikes.\n"
                "PLAN: Surgical evaluation for anterior temporal lobectomy."
            )

        doc = Document(
            patient_id=patient.id,
            filename="clinical_summary.txt",
            original_filename="clinical_summary.txt",
            file_path=str(note_path),
            status=DocumentStatus.UPLOADED
        )
        db.session.add(doc)
        db.session.commit()

        yield app, app.test_client(), patient.id, doc.id

        db.session.remove()
        db.drop_all()

def test_embedding_service():
    embedder = EmbeddingService(dimension=384)
    vec = embedder.embed_text("Epileptic seizure evaluation")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)
    norm = np.linalg.norm(vec)
    assert abs(norm - 1.0) < 1e-4

def test_vector_store(tmp_path):
    store = VectorStoreService(storage_dir=tmp_path, dimension=384)
    embedder = EmbeddingService(dimension=384)
    
    texts = ["Left temporal lobe epilepsy", "Cardiology echocardiogram normal"]
    vectors = embedder.embed_batch(texts)
    meta = [
        {"chunk_id": "c1", "text": texts[0], "section": "Neuro"},
        {"chunk_id": "c2", "text": texts[1], "section": "Cardio"}
    ]
    
    store.add_chunks(patient_id=1, vectors=vectors, chunks_meta=meta)
    
    q_vec = embedder.embed_text("epilepsy temporal seizures")
    results = store.search(patient_id=1, query_vector=q_vec, top_k=1)
    
    assert len(results) == 1
    assert "temporal lobe" in results[0]["text"]
    assert results[0]["score"] > 0.0

def test_rag_requires_gemini_key(app_and_client):
    app, client, patient_id, doc_id = app_and_client
    
    with app.app_context():
        # Ensure no key is set
        GeminiService.set_runtime_key("")
        
        # Query via client without key
        res = client.post(f"/api/patients/{patient_id}/ask", json={
            "question": "Summarize the findings."
        })
        assert res.status_code == 400
        assert "Gemini AI API Key Required" in res.get_json()["error"]

def test_end_to_end_rag_with_gemini(app_and_client):
    app, client, patient_id, doc_id = app_and_client
    
    with app.app_context():
        rag = RAGService()
        # 1. Index document
        proc_res = rag.process_and_index_document(doc_id)
        assert proc_res["success"] is True
        assert proc_res["status"] == DocumentStatus.INDEXED

        # Mock Gemini generation
        mock_answer = "Left mesial temporal spikes recorded with video-EEG concordance."
        with patch.object(GeminiService, "generate_grounded_answer", return_value=(mock_answer, True)):
            # Set test key
            GeminiService.set_runtime_key("AIzaSyTestMockKey12345")

            # 2. Ask question
            report = rag.ask_grounded_question(
                patient_id=patient_id,
                question="Summarize the important findings from the previous report.",
                api_key="AIzaSyTestMockKey12345"
            )
            assert report is not None
            assert report.status == ReportStatus.GENERATED
            assert report.is_grounded is True
            assert len(report.sources) > 0

            # 3. Test approval endpoint via client
            appr_res = client.post(f"/api/reports/{report.id}/approve", json={
                "answer": "Verified findings: Left mesial temporal spikes and refractory focal seizures.",
                "reviewer_notes": "Corroborated with EEG video telemetry."
            })
            assert appr_res.status_code == 200
            approved_data = appr_res.get_json()["report"]
            assert approved_data["status"] == ReportStatus.APPROVED

            # 4. Export PDF
            pdf_path = ExportService.export_pdf(db.session.get(Report, report.id))
            assert pdf_path.exists()
            assert pdf_path.stat().st_size > 500
