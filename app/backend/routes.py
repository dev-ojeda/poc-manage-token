#!/usr/bin/env python
# -*- coding: utf-8 -*-


from datetime import datetime, timezone

from bson import ObjectId
from app.auth.services.auth_service import AuthService
from app.auth.services.user_service import UserService
from app.model.token_generator import TokenGenerator
from app.utils.db_manager import DbManager
from flask import Blueprint, jsonify, make_response, request
from icecream import ic

from app.auth.services.session_service import SessionService
from app.midleware.jwt_guard import jwt_required_custom, jwt_required_custom_refresh, log_refresh_attempt
from app.model.user import User
from app.model.user_session import UserSession

backend_bp = Blueprint("backend", __name__)
MAX_ATTEMPTS = 3
BLOCK_TIME_SECONDS = 120  # 2 min

def update_datetime_format_iso(fecha: datetime) -> datetime:
     return fecha.fromisoformat(fecha.isoformat())

@backend_bp.route("/auth/acceso", methods=["POST"])
def login():
    us = UserService()
    data = request.get_json()
    user_agent = data.get("user_agent")
    browser = user_agent.get("browser")
    so = user_agent.get("os")
    ip_address = request.remote_addr
    if not request.is_json:
        return jsonify({"msg": "Content-Type debe ser application/json", "code": "INVALID_JSON"})

    missing = us.validate_login_payload(data)
    if missing:
        return jsonify({"msg": f"Faltan campos: {', '.join(missing)}", "code": "MISSING_FIELDS"})

    tg = TokenGenerator()
    user_model = us.get_user_by_username(username=data.get("username"))
    if not user_model:
        return jsonify({"msg": "Usuario no encontrado"}), 403

    if user_model.is_blocked_now():
        return jsonify({
            "msg": "⏳ Usuario temporalmente bloqueado",
            "bloqueado_hasta": user_model.blocked_until.isoformat() + "Z",
            "code": "USER_BLOCKED"
        })

    
    validate_fail_credentials = us.handle_failed_login(user_model=user_model)
    if not validate_fail_credentials.get("success"):
        return jsonify({"msg": validate_fail_credentials.get("message"), "code": "INVALID_FAIL_CREDENTIALS"})

    validate_attempts = us.reset_login_attempts(user_model=user_model)
    if not validate_attempts.get("success"):
        return jsonify({"msg": validate_attempts.get("message"), "code": "INVALID_RESET_ATTEMPS"})
    access_token, refresh_token = tg.create_tokens({
        "username": user_model.username,
        "jti": None,
        "device_id": data["device"],
        "rol": user_model.rol
    })

    decoded = tg.verify_token(access_token, expected_type="access")
    
    validate_upsert_user_token = us.persist_refresh_token(
        decoded, 
        refresh_token, 
        user_agent, 
        ip_address)
    if not validate_upsert_user_token.get("success"):
        return jsonify({"msg": validate_upsert_user_token.get("message"), "code": "INVALID_UPSERT_TOKENS"})


    # Crear instancia de sesión
    user_model_session = UserSession(
        user_id=user_model.id,
        device_id=decoded.get("device_id"),
        ip_address=ip_address,
        browser=browser,
        os=so,
        login_at=update_datetime_format_iso(datetime.now(timezone.utc)),
        last_refresh_at=update_datetime_format_iso(datetime.now(timezone.utc)),
        refresh_token=refresh_token,
        role="User"
    )
    ic(f"[USER SESSION]: {user_model_session}")
    ss = SessionService()
    insert_result = ss.register_session(user_session=user_model_session)
    if not insert_result.get("success"):
        return jsonify({"msg": insert_result.get("message"), "code": "INVALID_REGISTER_USER"})
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "device_id": decoded.get("device_id"),
        "rol": user_model.rol
    }), 200

@backend_bp.route("/auth/refresh", methods=["POST"])
@log_refresh_attempt
def refresh():
    service = AuthService()
    data = request.get_json()
   
    if not data:
        return jsonify({"msg": "JSON inválido o vacío", "code": "INVALID_JSON"}), 400

    refresh_token = data.get("refresh_token")
    device_id = str(data.get("device_id", "")).strip()
    user_agent = str(request.headers.get("User-Agent")).strip()
    ip = request.remote_addr

    if not refresh_token or not device_id:
        return jsonify({"msg": "Faltan datos requeridos", "code": "MISSING_FIELDS"}), 400

    try:
        # Verificar existencia en base de datos
        stored = service.get_refresh_token_from_db(refresh_token)
        if not stored:
            return jsonify({"msg": "Token no válido. Iniciá sesión nuevamente.", "code": "InvalidTokenError"}), 401

        # Detectar reuso
        if service.detect_reuse(stored):
            service.revoke_all_for_device(device_id)
            return jsonify({"msg": "Reuso detectado", "code": "ReuseDetected"}), 401

        # Validaciones adicionales
        if service.device_mismatch(stored, device_id):
            return jsonify({"msg": "Dispositivo no coincide", "code": "DeviceMismatch"}), 403

        if stored.get("revoked_at"):
            return jsonify({"msg": "Token revocado", "code": "RevokedToken"}), 401

        if stored.get("refresh_attempts", 0) >= 3:
            return jsonify({"msg": "Se alcanzó el máximo de intentos de refresh", "code": "MaxAttemptsExceeded"}), 403

        # Verificar firma y tipo del token
        payload = service.get_token_payload(refresh_token)
        if service.is_token_expired(payload):
            return jsonify({"msg": "Token expirado", "code": "Expired"}), 401
        username, jti = payload["sub"], payload["jti"]
        # Marcar el token actual como usado
        if not service.mark_used(
            username=username,
            device_id=device_id,
            jti=jti,
            refresh_token=refresh_token,
            created_at=stored["created_at"],
            expires_at=stored["expires_at"]
        ):
            return jsonify({"msg": "Error al marcar usado", "code": "MarkUsedError"}), 500

        # Validar aún vigente y no revocado
        if not service.is_valid_refresh(refresh_token, device_id):
            return jsonify({"msg": "Token inválido", "code": "RevokedToken"}), 401

        # Revocar el token anterior (si corresponde)
        if not service.revoke_old_token(username, device_id, jti, refresh_token):
            return jsonify({"msg": "Error al revocar", "code": "RevokeError"}), 500

        # Generar nuevos tokens
        access_token, new_refresh_token = service.generate_tokens({
            "username": username,
            "jti": None,
            "device_id": device_id,
            "rol": stored.get("rol")
        })

        # Upsert del nuevo refresh
        attempts = stored.get("refresh_attempts", 0) + 1
        if not service.upsert_new_token(
            username=username,
            device_id=device_id,
            jti=jti,
            refresh_token=new_refresh_token,
            user_agent=user_agent,
            ip_address=ip,
            refresh_attempts=attempts
        ):
            return jsonify({"msg": "Error al guardar el nuevo token", "code": "UpsertError"}), 500

        # Extraer info y responder
        decoded = service.get_token_payload(new_refresh_token)
        return jsonify({
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "device_id": decoded.get("device_id"),
            "username": decoded.get("username"),
            "rol": decoded.get("rol"),
            "exp": decoded.get("exp")
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error interno: {str(e)}", "code": "InternalServerError"}), 500


@backend_bp.route("/auth/logout", methods=["POST"])
@jwt_required_custom_refresh
def logout(user,user_token_refresh):
    us = UserService()
    ss = SessionService()
    gt = TokenGenerator()
    dm = DbManager()
    data = request.get_json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    device_id = data.get("device_id")
    reason = data.get("reason")
    ic(f"🔐 Logout → refresh_token: {refresh_token}, device_id: {device_id}")
    if str(user_token_refresh).__ne__(refresh_token):
        ic("❌ Token de acceso faltante")
        return jsonify({"msg": "Token de acceso faltante"}), 403

    client_ip = request.remote_addr

    try:

        username = user.get("username")

        # 🔐 Marcar refresh_token como revocado
        update_revoked_token = dm.update_store_refresh_token_revoked(username,device_id)
        if not update_revoked_token["success"]:
            return jsonify({"msg": update_revoked_token.get("message"), "code": "INVALID_REVOKED_TOKEN"})
        # 🔒 Revocar access_token
        update_revoked_token_blacklist = dm.revoke_token(access_token,device_id,username,reason)
        if not update_revoked_token_blacklist["success"]:
            return jsonify({"msg": update_revoked_token_blacklist.get("message"), "code": "INVALID_REVOKED_TOKEN_BLACKLIST"})
        # 📝 Log opcional (auditoría)
        
        user_model: User = us.get_user_by_username(username=username)
        user_sesion = ss.update_session(user_id=ObjectId(user_model.id))
        if not user_sesion["success"]:
            return jsonify({"msg": user_sesion.get("message"), "code": "INVALID_SESSION_CLOSED"})
        ic(f"🔒 Logout: {username} desde IP {client_ip} usando device_id {device_id}")
        response = make_response(jsonify({"msg": "Sesion Cerrada con exito"}), 200)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

    except Exception as e:
        ic(f"❌ Error en logout: {str(e)}")
        return jsonify({"msg": f"Token inválido o sesión corrupta: {str(e)}"}), 400

@backend_bp.route("/auth/dashboard", methods=["GET"])
@jwt_required_custom
def dashboard(user):
    ic(user)
    return jsonify({
        "username": user.get("username"),
        "rol": user.get("rol"),
        "device_id": user.get("device_id"),
        "exp": user.get("exp"),
        "jti": user.get("jti")
    }),200