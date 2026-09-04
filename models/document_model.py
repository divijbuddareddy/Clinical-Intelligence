from datetime import datetime, timezone
from models.database import db

def utc_now():
    return datetime.now(timezone.utc)

class DocumentStatus:
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"

class DocumentType:
    CLINICAL_NOTE = "CLINICAL_NOTE"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    LAB_REPORT = "LAB_REPORT"
    PATHOLOGY_REPORT = "PATHOLOGY_REPORT"
    CONSULTATION_NOTE = "CONSULTATION_NOTE"
    GENERAL = "GENERAL"

class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    filename = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    document_type = db.Column(db.String(64), nullable=False, default=DocumentType.CLINICAL_NOTE)
    file_size = db.Column(db.Integer, default=0)
    page_count = db.Column(db.Integer, default=1)
    status = db.Column(db.String(32), nullable=False, default=DocumentStatus.UPLOADED)
    error_message = db.Column(db.Text, nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    processed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    chunks = db.relationship("DocumentChunk", backref="document", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "document_type": self.document_type,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "status": self.status,
            "chunk_count": len(self.chunks),
            "error_message": self.error_message,
            "uploaded_by": self.uploaded_by,
            "uploader_name": self.uploader.name if self.uploader else "System",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }

class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    section_title = db.Column(db.String(256), nullable=True, default="General Section")
    page_number = db.Column(db.Integer, nullable=True, default=1)
    vector_reference = db.Column(db.String(128), nullable=True)
    token_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "section_title": self.section_title,
            "page_number": self.page_number,
            "vector_reference": self.vector_reference,
            "document_filename": self.document.original_filename if self.document else "Unknown",
        }
