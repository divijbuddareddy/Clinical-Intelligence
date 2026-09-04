from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db

def utc_now():
    return datetime.now(timezone.utc)

class UserRole:
    DOCTOR = "DOCTOR"
    CLINICAL_STAFF = "CLINICAL_STAFF"
    ADMIN = "ADMIN"
    ALL_ROLES = [DOCTOR, CLINICAL_STAFF, ADMIN]

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), nullable=False, default=UserRole.DOCTOR)
    specialty = db.Column(db.String(120), nullable=True, default="General Medicine")
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    uploaded_documents = db.relationship("Document", backref="uploader", lazy=True)
    reviewed_reports = db.relationship("Report", backref="reviewer", lazy=True)
    audit_logs = db.relationship("AuditLog", backref="user", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "specialty": self.specialty,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
