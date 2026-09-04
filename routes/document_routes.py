import os
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
from config import Config
from models.database import db
from models.patient_model import Patient
from models.document_model import Document, DocumentStatus, DocumentType
from models.audit_model import log_audit, AuditAction
from services.rag_service import RAGService

document_bp = Blueprint("document_bp", __name__)
rag_service = RAGService()

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@document_bp.route("/api/patients/<int:patient_id>/documents", methods=["GET"])
def list_patient_documents(patient_id: int):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    docs = Document.query.filter_by(patient_id=patient_id).order_by(Document.created_at.desc()).all()
    return jsonify({
        "documents": [d.to_dict() for d in docs],
        "total": len(docs)
    }), 200

@document_bp.route("/api/patients/<int:patient_id>/documents", methods=["POST"])
def upload_document(patient_id: int):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded in form data"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not supported. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"}), 400

    raw_filename = secure_filename(file.filename) or f"doc_{uuid.uuid4().hex[:8]}.pdf"
    doc_type = request.form.get("document_type", DocumentType.CLINICAL_NOTE)
    auto_process = request.form.get("auto_process", "true").lower() == "true"

    # Patient directory
    patient_dir = Config.UPLOAD_FOLDER / f"patient_{patient_id}"
    patient_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4().hex[:6]}_{raw_filename}"
    file_path = patient_dir / unique_filename
    file.save(str(file_path))

    file_size = file_path.stat().st_size
    user_id = session.get("user_id")

    doc = Document(
        patient_id=patient_id,
        filename=unique_filename,
        original_filename=raw_filename,
        file_path=str(file_path),
        document_type=doc_type,
        file_size=file_size,
        status=DocumentStatus.UPLOADED,
        uploaded_by=user_id
    )
    db.session.add(doc)
    db.session.commit()

    log_audit(
        action=AuditAction.DOC_UPLOAD,
        resource_type="Document",
        resource_id=doc.id,
        details=f"Uploaded {raw_filename} ({file_size} bytes) for patient {patient.patient_code}",
        user_id=user_id,
        ip=request.remote_addr
    )

    # Process immediately if auto_process is enabled
    processing_result = None
    if auto_process:
        try:
            processing_result = rag_service.process_and_index_document(doc.id, user_id=user_id)
        except Exception as e:
            print(f"Auto-processing error for doc {doc.id}: {e}")

    return jsonify({
        "message": "Document uploaded successfully",
        "document": doc.to_dict(),
        "processing_result": processing_result
    }), 201

@document_bp.route("/api/documents/<int:doc_id>/process", methods=["POST"])
def process_document(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    user_id = session.get("user_id")
    try:
        res = rag_service.process_and_index_document(doc_id, user_id=user_id)
        return jsonify({
            "message": "Document processed and indexed successfully into FAISS",
            "document": doc.to_dict(),
            "result": res
        }), 200
    except Exception as e:
        return jsonify({"error": f"Document processing failed: {str(e)}"}), 500

@document_bp.route("/api/documents/<int:doc_id>/view", methods=["GET"])
def view_document_content(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    chunks = [c.to_dict() for c in doc.chunks]
    return jsonify({
        "document": doc.to_dict(),
        "chunks": chunks,
        "total_chunks": len(chunks)
    }), 200

@document_bp.route("/api/documents/<int:doc_id>/download", methods=["GET"])
def download_document(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc or not Path(doc.file_path).exists():
        return jsonify({"error": "File not found on server"}), 404

    return send_file(
        doc.file_path,
        as_attachment=True,
        download_name=doc.original_filename
    )

@document_bp.route("/api/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    patient_id = doc.patient_id
    filename = doc.original_filename

    try:
        # 1. Remove vector store index references
        rag_service.vector_store.remove_document_chunks(patient_id, doc_id)

        # 2. Remove physical file if exists
        try:
            p = Path(doc.file_path)
            if p.exists():
                p.unlink()
        except Exception as e:
            print(f"File delete note: {e}")

        # 3. Delete database record
        db.session.delete(doc)
        db.session.commit()

        user_id = session.get("user_id")
        log_audit(
            action=AuditAction.DOC_DELETE,
            resource_type="Document",
            resource_id=doc_id,
            details=f"Deleted document '{filename}' for patient ID {patient_id}",
            user_id=user_id,
            ip=request.remote_addr
        )

        return jsonify({"message": f"Document '{filename}' deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete document: {str(e)}"}), 500
