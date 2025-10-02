#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from datetime import timezone
import logging

from bson import ObjectId
from icecream import ic
from app import limiter
from app.auth.services.audit_service import AuditService
from app.auth.services.item_service import ItemService
from app.auth.services.session_service import SessionService
from app.auth.services.auth_service import AuthService
from app.auth.services.blacklist_service import TokenBlacklistService
from app.auth.services.user_service import UserService
from flask import Blueprint, jsonify, request
from app.midleware.jwt_guard import jwt_required_custom
from app.model.item_model import ItemModel
from app.model.user_model import UserModel
from app.model.user_session_model import UserSessionModel

backend_bp = Blueprint("backend", __name__)

# -----------------------
# Helpers
# -----------------------
def iso_now() -> datetime.datetime:
    return datetime.datetime.now(tz=timezone.utc)

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

def existe_usuario(user_id: ObjectId) -> UserSessionModel | None:
    session_service = SessionService()
    result = session_service.get_active_session_by_Id(user_id=user_id)
    return UserSessionModel.from_dict(result) if result else None

class UserEndpoints:
    def __init__(self):
        self.logger = logging.getLogger(f"ENDPOINTS_USER.{self.__class__.__name__}")
    @staticmethod
    @limiter.limit("5 per minute")
    def login():
        user_service = UserService()
        session_service = SessionService()
        audit_service = AuditService()
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
        ip = request.remote_addr or "127.0.0.1"
        browser, so = get_user_agent_info(user_agent)
        result = user_service.get_user_login(username, password, device_id, user_agent, ip)

        if not result.get("success"):
            return json_response(success=False,message=result.get("msg"), code=result.get("code"), status=int(result.get("status")))

        # Crear o actualizar sesión
        user_session = UserSessionModel(
            user_id=result["data"]["_id"],
            device_id=device_id,
            ip_address=ip,
            browser=browser,
            os=so,
            login_at=iso_now(),
            refresh_token=result["refresh_token"],
            last_refresh_at=iso_now(),
            reason="login",
            role=result["data"]["rol"]
        )
        existing = session_service.get_active_session_by_id(user_session._user_id)
        if existing["data"] is not None:
            audit_service.update_session_activity(user_id=user_session._user_id, ip_address=ip, user_agent=browser, reason="login")
        else:
            inserted = session_service.register_session(user_session=user_session)
            if not inserted.get("success"):
                return json_response(success=False, message=inserted.get("message"), code="REGISTER_SESSION_FAILED", status=500)

        return jsonify({
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "device_id": device_id,
            "rol":result["data"]["rol"]
        }), 200

    @staticmethod
    @jwt_required_custom
    def refresh(user):
        user_service = UserService()
        auth_service = AuthService()
        session_service = SessionService()
        audit_service = AuditService()

        data, error = get_request_data()
        if error:
            return error

        refresh_token = data.get("refresh_token")
        device_id = str(data.get("device_id", "")).strip()
        browser, so = get_user_agent_info(data.get("user_agent", {}))
        ip = request.remote_addr

        if not refresh_token or not device_id:
            return json_response("Faltan datos requeridos", "MISSING_FIELDS")

        # Verificar token en DB
        stored = auth_service.get_refresh_token(refresh_token=refresh_token)
        if not stored:
            return json_response("Token no válido. Iniciá sesión nuevamente.", "InvalidTokenError", 401)

        if stored.get("revoked_at"):
            return json_response("Token revocado", "RevokedToken", 401)

        in_use = auth_service.get_active_token_by_user_and_device(username=user["sub"], device_id=device_id)
        if not in_use:
            return json_response("Dispositivo no coincide", "DeviceMismatch", 403)

        if stored.get("refresh_attempts", 0) >= 2:
            return json_response("Se alcanzó el máximo de intentos de refresh", "MaxAttemptsExceeded", 403)

        # Validar expiración
        try:
            payload = auth_service.get_token_payload(token=refresh_token)
        except Exception as e:
            return json_response(f"Token inválido: {str(e)}", "InvalidTokenPayload", 401)

        if auth_service.is_token_expired(exp=float(payload.get("exp", 0))):
            return json_response("Token expirado", "Expired", 401)

        username, jti = payload.get("sub"), payload.get("jti")

        # Revocar token antiguo
        revoked = auth_service.revoke_old_token(username=username, device_id=device_id, token=refresh_token)
        if not revoked.get("success"):
            return json_response("No se pudo revocar token antiguo", "REVOKED_OLD_TOKEN_FAILED", 500)

        # Generar nuevos tokens
        access_token, new_refresh_token = auth_service.generate_tokens({
            "username": username,
            "jti": jti,
            "device_id": device_id,
            "rol": payload.get("rol")
        })

        # Persistir refresh token
        attempts = stored.get("refresh_attempts", 0) + 1
        upsert = auth_service.upsert_new_token(
            username=username,
            device_id=device_id,
            jti=jti,
            refresh_token=new_refresh_token,
            browser=browser,
            os=so,
            ip_address=ip,
            refresh_attempts=attempts
        )
        if not upsert.get("success"):
            return json_response("Error guardando token", "UPSERT_TOKEN_FAILED", 500)

        # Actualizar sesión y auditoría
        user_model = user_service.get_user_by_username(username=username)
        if not user_model:
            return json_response("Usuario inexistente", "INVALID_USER_TOKEN", 500)

        session_res = session_service.update_session(user_id=ObjectId(user_model.id), token=new_refresh_token, reason="refresh_token")
        if not session_res.get("success"):
            return json_response("Error actualizando sesión", "INVALID_UPDATE_USER", 500)

        audit_service.update_session_activity(user_id=user_model.id, ip_address=ip, user_agent=browser, reason="refresh_token")

        decoded = auth_service.get_token_payload(new_refresh_token)
        return jsonify({
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "device_id": decoded.get("device_id"),
            "username": decoded.get("sub"),
            "rol": decoded.get("rol"),
            "exp": decoded.get("exp")
        }), 200

    @staticmethod
    @jwt_required_custom
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
    @jwt_required_custom
    def create_item(user):
        user_service = UserService()
        item_service = ItemService()

        data, error = get_request_data()
        if error:
            return error

        data["user_id"] = user["sub"]

        # Validar payload
        missing = item_service.validate_item_payload(data)
        if missing:
            return json_response(f"Faltan campos: {', '.join(missing)}", "MISSING_FIELDS")

        # Obtener usuario
        user_model: UserModel = user_service.get_user_by_username(username=data["user_id"])
        if not user_model:
            return json_response("Usuario inexistente", "INVALID_USER", 404)

        # Crear item
        item_model = ItemModel(
            user_id=user_model.id,
            name=data.get("name"),
            description=data.get("description")
        )
        insert_result = item_service.insert_item(item_model=item_model)
        if not insert_result.get("success"):
            return json_response(insert_result.get("message"), "INSERT_ITEM_FAILED", 500)

        return jsonify({"msg": "Item creado correctamente"}), 201

    @staticmethod
    @jwt_required_custom
    def list_items(user):
        user_service = UserService()
        item_service = ItemService()

        # Obtener usuario
        user_model: UserModel = user_service.get_user_by_username(username=user["sub"])
        if not user_model:
            return json_error("Usuario inexistente", "INVALID_USER", 404)

        # Obtener items
        all_items = item_service.get_all_by_user(user_id=str(user_model.id))
        # result = []
        result = [
            {
                "item_id": str(item["item_id"]),
                "user_id": str(item["user_id"]),
                "name": item["name"],
                "description": item["description"]
            }
            for item in all_items["data"]
        ]

        return jsonify({"count": len(result), "items": result}), 200

    @staticmethod
    @jwt_required_custom
    def close(user):
        user_service = UserService()
        session_service = SessionService()
        audit_service = AuditService()
        auth_service = AuthService()
        blacklist_service = TokenBlacklistService()

        data = request.get_json(silent=True) or {}
        ic(f"Logout recibido: {data}")

        username = user.get("sub")
        jti = user.get("jti")
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        device_id = data.get("device_id")
        reason = data.get("reason", "logout")
        browser, so = get_user_agent_info(data.get("user_agent", {}))
        client_ip = request.remote_addr

        if not access_token and not refresh_token:
            return json_response("Debe incluir al menos un token", "MISSING_TOKEN")

        try:
            # Revocar tokens en bloque
            if refresh_token:
                decoded_refresh = auth_service.get_token_payload(refresh_token)
                revoked_refresh = auth_service.revoke_old_token(
                    username=username,
                    token=refresh_token,
                    jti=decoded_refresh.get("jti"),
                    upsert=True
                )
                if not revoked_refresh.get("success"):
                    return json_response(success=False, message=revoked_refresh.get("message"), code="INVALID_REVOKED_TOKEN", status=404)

            if access_token:
                revoked_access = blacklist_service.revoke_token_blacklist(
                    token=access_token,
                    device_id=device_id,
                    username=username,
                    reason=reason
                )
                if not revoked_access.get("success"):
                    return json_response(revoked_access.get("message"), "INVALID_REVOKED_TOKEN_BLACKLIST")

            # Actualizar sesión y auditoría
            user_model = user_service.get_user_by_username(username=username)
            if user_model:
                user_id = user_model.id if isinstance(user_model.id, ObjectId) else ObjectId(user_model.id)

                session_service.update_session(
                    user_id=user_id,
                    token=refresh_token,
                    reason=reason
                )
                audit_service.update_session_activity(
                    user_id=user_id,
                    ip_address=client_ip,
                    user_agent=browser,
                    reason="close"
                )

            return jsonify({
                "success": True,
                "message": f"Sesión cerrada ({reason})",
                "timestamp": iso_now().isoformat()
            }), 200

        except Exception as e:
            logging.exception("[Logout] Error inesperado")
            return json_response(f"Error al cerrar sesión: {e}", "LOGOUT_ERROR")


user_endpoints = UserEndpoints()

backend_bp.add_url_rule("/auth/acceso", view_func=user_endpoints.login, methods=["POST"], endpoint="user_login")
backend_bp.add_url_rule("/auth/refresh", view_func=user_endpoints.refresh, methods=["POST"], endpoint="user_refresh_token")
backend_bp.add_url_rule("/auth/dashboard", view_func=user_endpoints.dashboard, methods=["GET"], endpoint="user_dashboard")
backend_bp.add_url_rule("/auth/user/items", view_func=user_endpoints.create_item, methods=["POST"], endpoint="user_create_items")
backend_bp.add_url_rule("/auth/user/items", view_func=user_endpoints.list_items, methods=["GET"], endpoint="user_list_items")
backend_bp.add_url_rule("/auth/logout", view_func=user_endpoints.close, methods=["POST"], endpoint="user_close")