from flask import Blueprint, request, jsonify, session
from models.database import db
from models.patient_model import Patient
from models.audit_model import log_audit, AuditAction

patient_bp = Blueprint("patient_bp", __name__)

@patient_bp.route("/api/patients", methods=["GET"])
def list_patients():
    query = request.args.get("search", "").strip()
    if query:
        patients = Patient.query.filter(
            (Patient.patient_code.ilike(f"%{query}%")) |
            (Patient.display_name.ilike(f"%{query}%")) |
            (Patient.primary_condition.ilike(f"%{query}%"))
        ).order_by(Patient.created_at.desc()).all()
    else:
        patients = Patient.query.order_by(Patient.created_at.desc()).all()

    return jsonify({
        "patients": [p.to_dict() for p in patients],
        "total": len(patients)
    }), 200

@patient_bp.route("/api/patients", methods=["POST"])
def create_patient():
    data = request.get_json() or {}
    patient_code = data.get("patient_code", "").strip().upper()
    display_name = data.get("display_name", "").strip()
    date_of_birth = data.get("date_of_birth", "").strip()
    gender = data.get("gender", "Unspecified").strip()
    primary_condition = data.get("primary_condition", "").strip()
    attending_physician = data.get("attending_physician", "").strip()

    if not patient_code or not display_name or not date_of_birth:
        return jsonify({"error": "Patient code, name, and date of birth are required"}), 400

    if Patient.query.filter_by(patient_code=patient_code).first():
        return jsonify({"error": f"Patient code '{patient_code}' already exists"}), 409

    patient = Patient(
        patient_code=patient_code,
        display_name=display_name,
        date_of_birth=date_of_birth,
        gender=gender,
        primary_condition=primary_condition,
        attending_physician=attending_physician
    )
    db.session.add(patient)
    db.session.commit()

    user_id = session.get("user_id")
    log_audit(
        action=AuditAction.PATIENT_CREATE,
        resource_type="Patient",
        resource_id=patient.id,
        details=f"Created patient {patient.display_name} ({patient.patient_code})",
        user_id=user_id,
        ip=request.remote_addr
    )

    return jsonify({
        "message": "Patient created successfully",
        "patient": patient.to_dict()
    }), 201

@patient_bp.route("/api/patients/<int:patient_id>", methods=["GET"])
def get_patient(patient_id: int):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    user_id = session.get("user_id")
    log_audit(
        action=AuditAction.PATIENT_VIEW,
        resource_type="Patient",
        resource_id=patient.id,
        details=f"Viewed patient record for {patient.patient_code}",
        user_id=user_id,
        ip=request.remote_addr
    )

    return jsonify({
        "patient": patient.to_dict(),
        "documents": [d.to_dict() for d in patient.documents],
        "reports": [r.to_dict() for r in patient.reports]
    }), 200
