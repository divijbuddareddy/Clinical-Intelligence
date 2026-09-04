from flask import Blueprint, request, jsonify, session
from models.database import db
from models.user_model import User, UserRole
from models.audit_model import log_audit, AuditAction

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user.id
    session["role"] = user.role
    session["user_name"] = user.name

    log_audit(
        action=AuditAction.USER_LOGIN,
        resource_type="User",
        resource_id=user.id,
        details=f"User {user.name} ({user.role}) logged in.",
        user_id=user.id,
        ip=request.remote_addr
    )

    return jsonify({
        "message": "Authentication successful",
        "user": user.to_dict()
    }), 200

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    user_id = session.get("user_id")
    if user_id:
        log_audit(
            action=AuditAction.USER_LOGOUT,
            resource_type="User",
            resource_id=user_id,
            details="User logged out.",
            user_id=user_id,
            ip=request.remote_addr
        )
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@auth_bp.route("/api/auth/me", methods=["GET"])
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False, "user": None}), 200

    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return jsonify({"authenticated": False, "user": None}), 200

    return jsonify({
        "authenticated": True,
        "user": user.to_dict()
    }), 200
