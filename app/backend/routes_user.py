#!/usr/bin/env python
# -*- coding: utf-8 -*-
from bson import ObjectId
from flask import Blueprint, jsonify, request
from app import limiter
from app.logging_config import get_logger
from app.helpers.helpers import (
    get_request_data,
    get_user_agent_info,
    iso_now,
    json_response,
    log_and_response,
)
from app.midleware.jwt_guard import jwt_user_required, log_endpoint, metrics_endpoint, rate_limit
from app.auth import get_auth_services
from app.model.item_model import ItemModel
from app.model.token_model import TokenModel
from app.model.user_session_model import UserSessionModel


user_bp = Blueprint("user", __name__,url_prefix="/api")
logger = get_logger("ENDPOINTS_USER")
services = get_auth_services()

class UserEndpoints:
    """Endpoints relacionados con usuarios autenticados."""

    @staticmethod
    @limiter.limit("5 per minute")
    @log_endpoint
    @metrics_endpoint
    def login():
        data, error = get_request_data()
        if error:
            return error

        required = ["username", "password", "device"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return log_and_response(
                False,
                f"Campos requeridos faltantes: {', '.join(missing)}",
                "MISSING_FIELDS",
                400,
                logger=logger,
            )

        username, password, device_id = data["username"], data["password"], data["device"]
        user_agent = data.get("user_agent", {})
        ip = request.remote_addr or "127.0.0.1"
        browser, so = get_user_agent_info(user_agent)

        result = services.user_service.get_user_login(username, password, device_id, user_agent, ip)
        if not result.get("success"):
            return log_and_response(
                success=False,
                message=result.get("msg"),
                code=result.get("code"),
                status=int(result.get("status")),
                logger=logger,
            )

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
            role=result["data"]["rol"],
        )

        existing = services.session_service.get_active_session_by_id(user_id=user_session._user_id, device_id=device_id)
        if existing.get("data"):
            services.audit_service.update_session_activity(
                user_id=user_session._user_id, ip_address=ip, user_agent=browser, reason="login"
            )
        else:
            inserted = services.session_service.register_session(user_session=user_session)
            if not inserted.get("success"):
                return log_and_response(
                    success=False,
                    message=inserted.get("message"),
                    code="REGISTER_SESSION_FAILED",
                    status=500,
                    logger=logger,
                )

        logger.info("Sesión iniciada correctamente")
        return jsonify(
            {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "device_id": device_id,
                "rol": result["data"]["rol"],
            }
        ), 200

    # ---------------------------------------------------------------------

    @staticmethod
    @jwt_user_required
    @log_endpoint
    def refresh(user: TokenModel):
        """Refresca tokens JWT activos."""
        data, error = get_request_data()
        if error:
            return error

        refresh_token = data.get("refresh_token")
        device_id = str(data.get("device_id", "")).strip()
        browser, so = get_user_agent_info(data.get("user_agent", {}))
        ip = request.remote_addr

        if not refresh_token or not device_id:
            return log_and_response(False, "Faltan datos requeridos", "MISSING_FIELDS", 401, logger=logger)

        stored = services.auth_service.get_refresh_token(refresh_token=refresh_token)
        if not stored or stored.get("revoked_at"):
            return log_and_response(False, "Token inválido o revocado", "InvalidToken", 401, logger=logger)

        in_use = services.auth_service.get_active_token_by_user_and_device(username=user.sub, device_id=device_id)
        if not in_use:
            return log_and_response(False, "Dispositivo no coincide", "DeviceMismatch", 403, logger=logger)

        if stored.get("refresh_attempts", 0) >= 2:
            return log_and_response(False, "Máximo de intentos de refresh alcanzado", "MaxAttemptsExceeded", 403, logger=logger)

        try:
            payload = services.auth_service.get_token_payload(token=refresh_token)
        except Exception as e:
            return log_and_response(False, f"Token inválido: {e}", "InvalidTokenPayload", 401, logger=logger)

        if services.auth_service.is_token_expired(exp=float(payload.get("exp", 0))):
            return log_and_response(False, "Token expirado", "Expired", 401, logger=logger)

        username, jti = payload["sub"], payload["jti"]

        revoked =services.auth_service.revoke_old_token(username=username, token=refresh_token, jti=jti, upsert=True)
        if not revoked.get("success"):
            return log_and_response(False, "No se pudo revocar el token antiguo", "REVOKE_FAILED", 500, logger=logger)

        access_token, new_refresh_token = services.auth_service.generate_tokens(
            {"username": username, "jti": jti, "device_id": device_id, "rol": payload.get("rol")}
        )

        attempts = stored.get("refresh_attempts", 0) + 1
        upsert = services.auth_service.upsert_new_token(
            username=username,
            device_id=device_id,
            jti=jti,
            refresh_token=new_refresh_token,
            user_agent=data.get("user_agent"),
            ip_address=ip,
            refresh_attempts=attempts,
        )
        if not upsert.get("success"):
            return log_and_response(False, "Error guardando token", "UPSERT_TOKEN_FAILED", 500, logger=logger)

        user_model = services.user_service.get_user_by_username(username=username)
        if not user_model:
            return log_and_response(False, "Usuario inexistente", "INVALID_USER_TOKEN", 500, logger=logger)

        session_res = services.session_service.update_session(
            user_id=ObjectId(user_model.id), token=new_refresh_token, reason="refresh_token"
        )
        if not session_res.get("success"):
            return log_and_response(False, "Error actualizando sesión", "UPDATE_SESSION_FAILED", 500, logger=logger)

        services.audit_service.update_session_activity(
            user_id=user_model.id, ip_address=ip, user_agent=browser, reason="refresh_token"
        )

        decoded = services.auth_service.get_token_payload(new_refresh_token)
        return jsonify(
            {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "device_id": decoded.device_id,
                "username": decoded.sub,
                "rol": decoded.rol,
                "exp": decoded.exp,
            }
        ), 200

    # ---------------------------------------------------------------------

    @staticmethod
    @jwt_user_required
    @log_endpoint
    @metrics_endpoint
    def dashboard(user):
        """Devuelve datos del usuario autenticado."""
        logger.info(f"Acceso dashboard user: {user.sub}")
        return jsonify(
            {
                "username": user.sub,
                "rol": user.rol,
                "device_id": user.device_id,
                "exp": user.exp,
                "jti": user.jti,
            }
        ), 200

    # ---------------------------------------------------------------------

    @staticmethod
    @jwt_user_required
    @log_endpoint
    @metrics_endpoint
    def create_item(user: TokenModel):
        """Crea un nuevo ítem para el usuario autenticado."""
        data, error = get_request_data()
        if error:
            return error

        data["user_id"] = user.sub
        missing = services.item_service.validate_item_payload(data)
        if missing:
            return json_response(False, f"Faltan campos: {', '.join(missing)}", "MISSING_FIELDS", 400)

        user_model = services.user_service.get_user_by_username(username=data["user_id"])
        if not user_model:
            return json_response(False, "Usuario inexistente", "INVALID_USER", 404)

        item_model = ItemModel(
            user_id=user_model.id,
            name=data.get("name"),
            description=data.get("description"),
        )
        insert_result = services.item_service.insert_item(item_model=item_model)
        if not insert_result.get("success"):
            return json_response(False, insert_result.get("message"), "INSERT_ITEM_FAILED", 500)

        logger.info("Item creado correctamente")
        return jsonify({"msg": "Item creado correctamente"}), 201

    # ---------------------------------------------------------------------

    @staticmethod
    @jwt_user_required
    @rate_limit
    @log_endpoint
    def list_items(user):
        user_model=services.user_service.get_user_by_username(username=user.sub)
        if not user_model:
            return json_response(False, "Usuario inexistente", "INVALID_USER", 404)

        all_items = services.item_service.get_all_by_user(user_id=str(user_model.id))
        items = [
            {
                "item_id": str(i["item_id"]),
                "user_id": str(i["user_id"]),
                "name": i["name"],
                "description": i["description"],
            }
            for i in all_items["data"]
        ]
        logger.info("Items enviados")
        return jsonify({"count": len(items), "items": items}), 200

    # ---------------------------------------------------------------------

    @staticmethod
    @jwt_user_required
    @log_endpoint
    @metrics_endpoint
    def close(user):
        """Cierra la sesión del usuario y revoca tokens."""

        data = request.get_json(silent=True) or {}
        logger.info(f"Logout recibido: {data}")

        username = user.sub
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        device_id = data.get("device_id")
        reason = data.get("reason", "logout")
        browser, so = get_user_agent_info(data.get("user_agent", {}))
        client_ip = request.remote_addr

        if not access_token and not refresh_token:
            return log_and_response(False, "Debe incluir al menos un token", "MISSING_TOKEN", 404, logger=logger)

        try:
            if refresh_token:
                decoded = services.auth_service.get_token_payload(refresh_token)
                revoked_refresh = services.auth_service.revoke_old_token(
                    username=username,
                    token=refresh_token,
                    jti=decoded.jti,
                    upsert=True,
                )
                if not revoked_refresh.get("success"):
                    return log_and_response(False, revoked_refresh.get("message"), "INVALID_REVOKE_REFRESH", 404, logger=logger)

            if access_token:
                revoked_access = services.blacklist_service.revoke_token_blacklist(
                    token=access_token, device_id=device_id, username=username, reason=reason
                )
                if not revoked_access.get("success"):
                    return log_and_response(False, revoked_access.get("message"), "INVALID_REVOKE_ACCESS", 404, logger=logger)

            user_model = services.user_service.get_user_by_username(username=username)
            if user_model:
                uid = ObjectId(user_model.id)
                services.session_service.update_session(user_id=uid, token=refresh_token, reason=reason)
                services.audit_service.update_session_activity(user_id=uid, ip_address=client_ip, device_id=device_id, user_agent=browser, reason=reason)

            logger.info(f"Sesión cerrada con éxito USER: {username}")
            return jsonify(
                {"success": True, "message": f"Sesión cerrada ({reason})", "timestamp": iso_now().isoformat()}
            ), 200

        except Exception as e:
            logger.exception("[Logout] Error inesperado")
            return log_and_response(False, f"Error al cerrar sesión: {e}", "LOGOUT_ERROR", 401, logger=logger)


# ---- Registro de rutas ----
user_endpoints = UserEndpoints()

user_bp.add_url_rule("/user/acceso", view_func=user_endpoints.login, methods=["POST"])
user_bp.add_url_rule("/user/refresh", view_func=user_endpoints.refresh, methods=["POST"])
user_bp.add_url_rule("/user/dashboard", view_func=user_endpoints.dashboard, methods=["GET"])
user_bp.add_url_rule("/user/items", view_func=user_endpoints.create_item, methods=["POST"])
user_bp.add_url_rule("/user/items", view_func=user_endpoints.list_items, methods=["GET"])
user_bp.add_url_rule("/user/logout", view_func=user_endpoints.close, methods=["POST"])

