from datetime import datetime, timezone
from models.database import db

def utc_now():
    return datetime.now(timezone.utc)

class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.String(32), nullable=False)
    gender = db.Column(db.String(32), nullable=True, default="Unspecified")
    primary_condition = db.Column(db.String(256), nullable=True)
    attending_physician = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    documents = db.relationship("Document", backref="patient", cascade="all, delete-orphan", lazy=True)
    reports = db.relationship("Report", backref="patient", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_code": self.patient_code,
            "display_name": self.display_name,
            "date_of_birth": self.date_of_birth,
            "gender": self.gender,
            "primary_condition": self.primary_condition,
            "attending_physician": self.attending_physician,
            "document_count": len(self.documents),
            "report_count": len(self.reports),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
