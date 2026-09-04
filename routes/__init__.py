from routes.auth_routes import auth_bp
from routes.patient_routes import patient_bp
from routes.document_routes import document_bp
from routes.report_routes import report_bp

__all__ = ["auth_bp", "patient_bp", "document_bp", "report_bp"]
