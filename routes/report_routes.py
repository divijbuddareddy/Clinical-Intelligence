from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session, send_file
from models.database import db
from models.patient_model import Patient
from models.document_model import Document
from models.report_model import Report, ReportStatus
from models.audit_model import AuditLog, log_audit, AuditAction
from services.rag_service import RAGService
from services.gemini_service import GeminiService
from services.export_service import ExportService

report_bp = Blueprint("report_bp", __name__)
rag_service = RAGService()

@report_bp.route("/api/ai/config", methods=["GET"])
def get_ai_config():
    session_key = session.get("gemini_api_key", "")
    runtime_key = GeminiService.get_runtime_key()
    active_key = session_key or runtime_key
    is_configured = bool(active_key and len(active_key) > 5)
    masked_key = f"{active_key[:4]}...{active_key[-4:]}" if is_configured and len(active_key) > 8 else ("Set" if is_configured else "Not Set")
    
    return jsonify({
        "configured": is_configured,
        "masked_key": masked_key,
        "model": GeminiService.get_runtime_model(),
        "available_models": ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro"]
    }), 200

@report_bp.route("/api/ai/config", methods=["POST"])
def update_ai_config():
    data = request.get_json() or {}
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "gemini-1.5-flash").strip()

    if not api_key:
        return jsonify({"error": "Gemini API key cannot be empty"}), 400

    # Validate key
    test_svc = GeminiService(api_key=api_key, model_name=model)
    is_valid, message = test_svc.validate_api_key()
    if not is_valid:
        return jsonify({"error": message}), 400

    # Save to session and runtime
    session["gemini_api_key"] = api_key
    GeminiService.set_runtime_key(api_key, model)

    return jsonify({
        "message": "Google Gemini API Key successfully validated and activated!",
        "configured": True,
        "model": model
    }), 200

@report_bp.route("/api/ai/clear-key", methods=["POST"])
def clear_ai_key():
    session.pop("gemini_api_key", None)
    GeminiService.set_runtime_key("", "gemini-1.5-flash")
    return jsonify({"message": "Gemini API key removed.", "configured": False}), 200

@report_bp.route("/api/patients/<int:patient_id>/ask", methods=["POST"])
def ask_patient_question(patient_id: int):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    data = request.get_json() or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400

    user_id = session.get("user_id")
    api_key = session.get("gemini_api_key") or GeminiService.get_runtime_key()

    # Ensure Gemini key is present
    if not api_key:
        return jsonify({
            "error": "Gemini AI API Key Required. Please set your Google Gemini API Key in the AI Settings (top right navbar) to enable grounded clinical analysis."
        }), 400

    # Ensure patient has documents indexed
    indexed_docs = Document.query.filter_by(patient_id=patient_id, status="INDEXED").count()
    if indexed_docs == 0:
        return jsonify({
            "error": "No indexed clinical documents found for this patient. Please upload and process documents first."
        }), 400

    try:
        report = rag_service.ask_grounded_question(
            patient_id=patient_id,
            question=question,
            user_id=user_id,
            api_key=api_key
        )
        return jsonify({
            "message": "AI Question answered with grounded citations",
            "report": report.to_dict()
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to answer question: {str(e)}"}), 500

@report_bp.route("/api/reports/<int:report_id>/review", methods=["POST"])
def review_report(report_id: int):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    data = request.get_json() or {}
    edited_answer = data.get("answer")
    reviewer_notes = data.get("reviewer_notes")

    if edited_answer is not None:
        report.answer = edited_answer
    if reviewer_notes is not None:
        report.reviewer_notes = reviewer_notes

    report.status = ReportStatus.UNDER_REVIEW
    report.reviewed_at = datetime.now(timezone.utc)
    report.reviewed_by = session.get("user_id")
    db.session.commit()

    log_audit(
        action=AuditAction.REPORT_REVIEW,
        resource_type="Report",
        resource_id=report.id,
        details=f"Report {report.id} marked as UNDER_REVIEW by user {session.get('user_id')}",
        user_id=session.get("user_id"),
        ip=request.remote_addr
    )

    return jsonify({
        "message": "Report updated and marked under review",
        "report": report.to_dict()
    }), 200

@report_bp.route("/api/reports/<int:report_id>/approve", methods=["POST"])
def approve_report(report_id: int):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    data = request.get_json() or {}
    edited_answer = data.get("answer")
    reviewer_notes = data.get("reviewer_notes")

    if edited_answer:
        report.answer = edited_answer
    if reviewer_notes:
        report.reviewer_notes = reviewer_notes

    report.status = ReportStatus.APPROVED
    report.approved_at = datetime.now(timezone.utc)
    report.reviewed_by = session.get("user_id")
    db.session.commit()

    log_audit(
        action=AuditAction.REPORT_APPROVE,
        resource_type="Report",
        resource_id=report.id,
        details=f"Report {report.id} approved by user {session.get('user_id')}",
        user_id=session.get("user_id"),
        ip=request.remote_addr
    )

    return jsonify({
        "message": "Report approved successfully by clinician",
        "report": report.to_dict()
    }), 200

@report_bp.route("/api/reports/<int:report_id>/export", methods=["GET"])
def export_report(report_id: int):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    export_format = request.args.get("format", "pdf").lower()
    user_id = session.get("user_id")

    # Mark as exported
    report.status = ReportStatus.EXPORTED
    report.exported_at = datetime.now(timezone.utc)
    db.session.commit()

    log_audit(
        action=AuditAction.REPORT_EXPORT,
        resource_type="Report",
        resource_id=report.id,
        details=f"Exported report {report.id} in {export_format.upper()} format",
        user_id=user_id,
        ip=request.remote_addr
    )

    if export_format == "json":
        return jsonify(ExportService.export_json(report)), 200

    try:
        pdf_path = ExportService.export_pdf(report)
        return send_file(
            str(pdf_path),
            as_attachment=True,
            download_name=f"Clinical_Report_{report.patient.patient_code}_{report.id}.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500

@report_bp.route("/api/reports", methods=["GET"])
def list_reports():
    patient_id = request.args.get("patient_id")
    status = request.args.get("status")

    query = Report.query
    if patient_id:
        query = query.filter_by(patient_id=int(patient_id))
    if status:
        query = query.filter_by(status=status)

    reports = query.order_by(Report.created_at.desc()).all()
    return jsonify({
        "reports": [r.to_dict() for r in reports],
        "total": len(reports)
    }), 200

@report_bp.route("/api/audit-logs", methods=["GET"])
def list_audit_logs():
    limit = int(request.args.get("limit", 50))
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return jsonify({
        "logs": [l.to_dict() for l in logs],
        "total": len(logs)
    }), 200

@report_bp.route("/api/stats", methods=["GET"])
def get_dashboard_stats():
    patient_count = Patient.query.count()
    doc_count = Document.query.count()
    indexed_doc_count = Document.query.filter_by(status="INDEXED").count()
    report_count = Report.query.count()
    pending_reviews = Report.query.filter(Report.status.in_(["GENERATED", "UNDER_REVIEW"])).count()
    approved_reports = Report.query.filter(Report.status.in_(["APPROVED", "EXPORTED"])).count()

    recent_reports = [r.to_dict() for r in Report.query.order_by(Report.created_at.desc()).limit(5).all()]
    recent_activity = [l.to_dict() for l in AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()]

    return jsonify({
        "metrics": {
            "patient_count": patient_count,
            "document_count": doc_count,
            "indexed_doc_count": indexed_doc_count,
            "report_count": report_count,
            "pending_reviews": pending_reviews,
            "approved_reports": approved_reports
        },
        "recent_reports": recent_reports,
        "recent_activity": recent_activity
    }), 200
