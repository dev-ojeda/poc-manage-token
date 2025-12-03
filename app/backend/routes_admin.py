#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from bson import ObjectId
from flask import Blueprint, jsonify, request
from icecream import ic
from app.helpers.helpers import get_request_data, json_response
from app import limiter
from app.auth.services import (
    AuditService,
    SessionService,
    AuthService,
    UserService,
)
from app.web_socket.event_socket import notificar_revocacion
from app.midleware.jwt_guard import jwt_admin_required

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")
logger = logging.getLogger(f"ENDPOINTS_ADMIN.{__name__}")

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
            logger.error(f"message: Campos requeridos faltantes: {', '.join(missing)} - code: MISSING_FIELDS")
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
            logger.error(f"{result.get("msg")}")
            return json_response(success=False,message=result.get("msg"), code=result.get("code"), status=int(result.get("status")))

        logger.info("Acceso Correcto")
        return jsonify({
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "device_id": device_id,
            "rol":result["data"]["rol"]
        })

    @staticmethod
    @jwt_admin_required
    def dashboard(user):
        if "error" in user:
            logger.error(f"{user.get("message")}")
            return json_response(False, user.get("message"), user.get("code"), 400)
        logger.info("Acceso a Dashboard-Admin Correcto")
        return jsonify({
            "username": user["sub"],
            "rol": user["rol"],
            "device_id": user["device_id"],
            "exp": user["exp"],
            "jti": user["jti"]
        }), 200

    @staticmethod
    @jwt_admin_required
    def get_audit_logs(user):
        try:
            audit_service = AuditService()
            result = audit_service.get_all_logs_audit()
            return jsonify({
                "msg": "✅ Logs obtenidos correctamente",
                "code": "SUCCESS",
                "total_count": result["total_count"],
                "logs": result["logs"]
            }), 200
        except Exception as e:
            logger.error(f"{str(e)}")
            return json_response(False, "❌ Error interno del servidor", "SERVER_ERROR", 500)

    @staticmethod
    @jwt_admin_required
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
            logger.error(f"{str(e)}")
            return json_response(False, "❌ Error interno del servidor", "SERVER_ERROR", 500)


    @staticmethod
    @jwt_admin_required
    def get_active_sessions(user):
        data = request.get_json() or {}
        filtro_status = data.get("filtro_status")
        try:
            session_service = SessionService()
            sessions = session_service.get_non_admin_active_sessions(filtro_status=filtro_status)
            logger.info(sessions["data"])
            return jsonify({"count": sessions["total_count"], "sessions": sessions["data"]})
        except Exception as e:
            logger.error(f"{str(e)}")
            return json_response(False, "❌ Error interno del servidor", "SERVER_ERROR", 500)

    @staticmethod
    @jwt_admin_required
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
admin_bp.add_url_rule("/auth/admin/audit", view_func=admin_endpoints.get_audit_logs, methods=["GET"], endpoint="admin_audit_logs")
admin_bp.add_url_rule("/auth/admin/user", view_func=admin_endpoints.get_users, methods=["POST"], endpoint="admin_users")
admin_bp.add_url_rule("/auth/sessions/active", view_func=admin_endpoints.get_active_sessions, methods=["POST"], endpoint="admin_active_sessions")
admin_bp.add_url_rule("/auth/sessions/revoke", view_func=admin_endpoints.revoke_session, methods=["POST"], endpoint="admin_revoke_session")
