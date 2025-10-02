#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
from uuid import uuid4
from bson import ObjectId
from flask import Blueprint, jsonify, request
from icecream import ic

from app import limiter
from app.auth.services.audit_service import AuditService
from app.auth.services.session_service import SessionService
from app.auth.services.auth_service import AuthService
from app.auth.services.user_service import UserService
from app.web_socket.event_socket import notificar_revocacion
from app.midleware.jwt_guard import admin_required
from app.model.user_model import UserModel
from app.model.token_generator_model import TokenGeneratorModel

admin_bp = Blueprint("admin_bp", __name__)

# -----------------------
# Helpers
# -----------------------
def iso_now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)

def json_response(success: bool, message: str, code: str, status: int = 200, **extra):
    """Formato de respuesta consistente."""
    base = {"success": success, "msg": message, "code": code, "status": status}
    base.update(extra)
    return jsonify(base), status

def get_request_data():
    if not request.is_json:
        return None, json_response(False, "Content-Type debe ser application/json", "INVALID_JSON", 400)
    return request.get_json(silent=True) or {}, None

def get_user_agent_info(user_agent: dict):
    return user_agent.get("browser"), user_agent.get("os")
# -----------------------------
# Endpoints
# -----------------------------
class AdminEndpoints:

    @staticmethod
    @limiter.limit("5 per minute")
    def login():
        user_service = UserService()
        data = request.get_json()

        data, error = get_request_data()
        if error:
            return error

        missing = user_service.validate_login_payload(data)
        if missing:
            return json_response(
                success=False,
                message=f"Campos requeridos faltantes: {', '.join(missing)}",
                code="MISSING_FIELDS",
                status=400
            )
        username = data.get("username")
        password = data.get("password")
        device_id = data.get("device")
        user_agent = data.get("user_agent", {})
        ip_address, device_id = request.remote_addr, data.get("device")
        result = user_service.get_user_login(username=username, password=password, device_id=device_id, user_agent=user_agent, ip=ip_address)
        if not result.get("success"):
            return json_response(success=False,message=result.get("msg"), code=result.get("code"), status=int(result.get("status")))

        return jsonify({
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "device_id": device_id,
            "rol":result["data"]["rol"]
        })

    @staticmethod
    @admin_required
    def dashboard(user):
        if "error" in user:
            return jsonify({"message": user.get("message"), "code": user.get("code")}), 400

        return jsonify({
            "username": user["sub"],
            "rol": user["rol"],
            "device_id": user["device_id"],
            "exp": user["exp"],
            "jti": user["jti"]
        }), 200

    @staticmethod
    @admin_required
    def get_audit_logs(user):
        try:
            audit_service = AuditService()
            result = audit_service.get_all_logs_audit()
            return jsonify({
                "msg": "✅ Logs obtenidos correctamente",
                "code": "SUCCESS",
                "total_count": result.get("total_count", 0),
                "logs": result.get("logs", [])
            }), 200
        except Exception as e:
            ic(e)
            return jsonify({"msg": "❌ Error interno del servidor", "code": "SERVER_ERROR"}), 500

    @staticmethod
    @admin_required
    def get_users(user):
        try:
            user_service = UserService()
            result = user_service.get_all_users()
            return jsonify({
                "msg": "✅ Users obtenidos correctamente",
                "code": "SUCCESS",
                "total_count": result.get("total_count", 0),
                "logs": result.get("logs", [])
            }), 200
        except Exception as e:
            ic(e)
            return jsonify({"msg": "❌ Error interno del servidor", "code": "SERVER_ERROR"}), 500

    @staticmethod
    @admin_required
    def get_active_sessions(user):
        data = request.get_json() or {}
        filtro_status = data.get("filtro_status")
        try:
            session_service = SessionService()
            sessions = session_service.get_non_admin_active_sessions(filtro_status=filtro_status)
            return jsonify({"count": len(sessions) or 0, "sessions": sessions})
        except Exception as e:
            ic(e)
            return jsonify({"msg": f"❌ Error al obtener sesiones: {str(e)}"}), 500

    @staticmethod
    @admin_required
    def revoke_session(user):
        data = request.get_json() or {}
        auth_service = AuthService()
        session_service = SessionService()
        audit_service = AuditService()

        session_id = data.get("user_id")
        username = data.get("username")
        device_id = data.get("device_id")
        user_rol = data.get("user_rol")
        user_agent = data.get("user_agent")
        refresh_token = data.get("refresh_token")
        ip_address = request.remote_addr

        if user_rol == user.get("rol") or device_id == user.get("device_id"):
            return jsonify({"msg": "Operación no permitida"}), 400

        result = auth_service.revoke_old_token(username=username, device_id=device_id, token=refresh_token)
        if not result.get("success"):
            return jsonify({"msg": result.get("message"), "code": "INVALID_REVOKED_REFRESH_TOKEN"}), 500

        result_revocar = session_service.revoke_session(user_id=ObjectId(session_id))
        validar_operacion = audit_service.update_session_activity(
            user_id=ObjectId(session_id),
            ip_address=ip_address,
            user_agent=user_agent,
            reason="revoked"
        )
        ic("[VALIDAR_OPERACION]", validar_operacion)

        notificar_revocacion(username)
        return jsonify({"msg": "Sesión revocada"}), 200


# -----------------------------
# Register routes
# -----------------------------
admin_endpoints = AdminEndpoints()

admin_bp.add_url_rule("/auth/admin", view_func=admin_endpoints.login, methods=["POST"], endpoint="admin_login")
admin_bp.add_url_rule("/auth/admin/dashboard", view_func=admin_endpoints.dashboard, methods=["GET"], endpoint="admin_dashboard")
admin_bp.add_url_rule("/auth/admin/audit", view_func=admin_endpoints.get_audit_logs, methods=["POST"], endpoint="admin_audit_logs")
admin_bp.add_url_rule("/auth/admin/user", view_func=admin_endpoints.get_users, methods=["POST"], endpoint="admin_users")
admin_bp.add_url_rule("/auth/sessions/active", view_func=admin_endpoints.get_active_sessions, methods=["POST"], endpoint="admin_active_sessions")
admin_bp.add_url_rule("/auth/sessions/revoke", view_func=admin_endpoints.revoke_session, methods=["POST"], endpoint="admin_revoke_session")
