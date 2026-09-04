import os
from flask import Flask, render_template, redirect, url_for, session, request
from config import Config
from models.database import db
from models.user_model import User
from models.patient_model import Patient
from models.document_model import Document
from models.report_model import Report
from models.audit_model import AuditLog
from routes.auth_routes import auth_bp
from routes.patient_routes import patient_bp
from routes.document_routes import document_bp
from routes.report_routes import report_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(report_bp)

    # Security Headers & Context Processors
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    @app.context_processor
    def inject_globals():
        user = None
        if "user_id" in session:
            user = db.session.get(User, session["user_id"])
        return {
            "current_user": user,
            "disclaimer": "Clinical Decision-Support Prototype. Not for autonomous clinical diagnosis or treatment."
        }

    # Frontend View Routes
    @app.route("/")
    def dashboard():
        if "user_id" not in session:
            return redirect(url_for("login_view"))
        return render_template("dashboard.html")

    @app.route("/login")
    def login_view():
        return render_template("login.html")

    @app.route("/patients")
    def patients_view():
        if "user_id" not in session:
            return redirect(url_for("login_view"))
        return render_template("patients.html")

    @app.route("/patients/<int:patient_id>")
    def patient_detail_view(patient_id):
        if "user_id" not in session:
            return redirect(url_for("login_view"))
        patient = Patient.query.get_or_404(patient_id)
        return render_template("patient_detail.html", patient=patient)

    @app.route("/reports-queue")
    def reports_queue_view():
        if "user_id" not in session:
            return redirect(url_for("login_view"))
        return render_template("reports.html")

    # Create tables
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
