import json
from datetime import datetime, timezone
from models.database import db

def utc_now():
    return datetime.now(timezone.utc)

class ReportStatus:
    GENERATED = "GENERATED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    EXPORTED = "EXPORTED"
    ALL_STATUSES = [GENERATED, UNDER_REVIEW, APPROVED, EXPORTED]

class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    raw_answer = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)  # Editable by reviewer
    sources_json = db.Column(db.Text, nullable=False, default="[]")  # JSON encoded list of citations
    status = db.Column(db.String(32), nullable=False, default=ReportStatus.GENERATED)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewer_notes = db.Column(db.Text, nullable=True)
    is_grounded = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    exported_at = db.Column(db.DateTime, nullable=True)

    @property
    def sources(self):
        try:
            return json.loads(self.sources_json or "[]")
        except Exception:
            return []

    @sources.setter
    def sources(self, value):
        self.sources_json = json.dumps(value or [])

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "patient_code": self.patient.patient_code if self.patient else "N/A",
            "patient_name": self.patient.display_name if self.patient else "N/A",
            "question": self.question,
            "raw_answer": self.raw_answer,
            "answer": self.answer,
            "sources": self.sources,
            "status": self.status,
            "is_grounded": self.is_grounded,
            "reviewed_by": self.reviewed_by,
            "reviewer_name": self.reviewer.name if self.reviewer else None,
            "reviewer_notes": self.reviewer_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "exported_at": self.exported_at.isoformat() if self.exported_at else None,
        }
