from datetime import datetime, timezone
from models.database import db

def utc_now():
    return datetime.now(timezone.utc)

class AuditAction:
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    PATIENT_CREATE = "PATIENT_CREATE"
    PATIENT_VIEW = "PATIENT_VIEW"
    DOC_UPLOAD = "DOC_UPLOAD"
    DOC_PROCESS = "DOC_PROCESS"
    DOC_DELETE = "DOC_DELETE"
    RAG_QUERY = "RAG_QUERY"
    REPORT_REVIEW = "REPORT_REVIEW"
    REPORT_APPROVE = "REPORT_APPROVE"
    REPORT_EXPORT = "REPORT_EXPORT"

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    resource_type = db.Column(db.String(64), nullable=False)  # Patient, Document, Report, User
    resource_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else "System",
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

def log_audit(action: str, resource_type: str, resource_id: str = None, details: str = None, user_id: int = None, ip: str = None):
    try:
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details,
            ip_address=ip
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Warning: Failed to log audit event: {e}")
