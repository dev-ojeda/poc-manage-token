#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from datetime import timezone
from uuid import uuid4

from bson import ObjectId
from app.auth import AuditService, SessionService, AuthService, TokenBlacklistService, UserService
from flask import Blueprint, jsonify, make_response, request
from icecream import ic 
from app.midleware.jwt_guard import jwt_required_custom
from app.model import UserModel, UserSessionModel

backend_bp = Blueprint("backend", __name__)
MAX_ATTEMPTS = 3
BLOCK_TIME_SECONDS = 120  # 2 min
def update_datetime_format_iso(fecha: datetime.datetime) -> datetime.datetime:
    return fecha.fromisoformat(fecha.isoformat())

def existe_usuario(user_id: ObjectId) -> UserSessionModel | None:
    session_service = SessionService()
    result = session_service.get_active_session_by_Id(user_id=user_id)
    return UserSessionModel.from_dict(result) if result else None

@backend_bp.route("/auth/acceso", methods=["POST"])
def login():
    user_service = UserService()
    session_service = SessionService()
    audit_service = AuditService()
    auth_service = AuthService()
    data = request.get_json()

    if not request.is_json:
        return jsonify({"msg": "Content-Type debe ser application/json", "code": "INVALID_JSON"}), 400

    # 1️⃣ Validación de payload
    missing = user_service.validate_login_payload(data)
    if missing:
        return jsonify({"msg": f"Faltan campos: {', '.join(missing)}", "code": "MISSING_FIELDS"}), 400

    user_agent = data.get("user_agent", {})
    browser, so = user_agent.get("browser"), user_agent.get("os")
    ip_address, device_id = request.remote_addr, data.get("device")

    user_model = UserModel(
            username=data.get("username"),
            password=data.get("password"),
            rol="User"
        )

    user_model: UserModel = user_service.get_user_by_username(username=user_model.username)

    if not user_model:
        return jsonify({"message": "No existe Usuario", "code": "INVALID_USER", "status": 401})

    # 2️⃣ Autenticación
    user_model: UserModel = user_service.authenticate_user(username=data.get("username"),password=data.get("password"),)
    
    if not user_model:
          # 4️⃣ Intentos fallidos
        fail_check = user_service.handle_failed_login(username=data.get("username"))
        if fail_check.get("success"):
            return jsonify({"message": "Usuario o contraseña inválidos", "code": "INVALID_CREDENTIALS", "status": 401})

    # 3️⃣ Bloqueo temporal
    if user_model.is_blocked_now():
        return jsonify({
            "msg": "⏳ Usuario temporalmente bloqueado",
            "bloqueado_hasta": float(user_model.blocked_until.timestamp()),
            "code": "USER_BLOCKED",
            "status": 403
        })

  

    # reset_attempts = user_service.reset_login_attempts(user_model=user_model)
    # if not reset_attempts.get("success"):
    #     return jsonify({"msg": reset_attempts.get("message"), "code": "INVALID_RESET_ATTEMPTS"}), 500

    # 5️⃣ Manejo de tokens
    existing_token = auth_service.is_token_in_use(user_model.username)
    if existing_token and existing_token["device_id"] == device_id:
        if auth_service.is_token_expired(exp=float(existing_token["expires_at"].timestamp())):
            # Token expirado → nuevo jti y tokens
            jti = str(uuid4())
            access_token, refresh_token = auth_service.generate_tokens({
                "username": user_model.username,
                "rol": user_model.rol,
                "device_id": device_id,
                "jti": jti
            })
            # Guardar refresh token
            upsert_ok = auth_service.upsert_new_token(
                username=user_model.username,
                device_id=device_id,
                refresh_token=refresh_token,
                jti=jti,
                ip_address=ip_address,
                browser=browser,
                os=so,
                refresh_attempts=0
            )
            if not upsert_ok.get("success"):
                return jsonify({"msg": upsert_ok.get("message"), "code": "UPSERT_TOKEN_FAILED"}), 500
        else:
            # Token válido → reutilizar jti, regenerar access
            jti = existing_token["jti"]
            refresh_token = existing_token["refresh_token"]
            access_token = auth_service.refresh_access_token(token=refresh_token)

    elif existing_token:
        # Otro device ya tiene token activo
        return jsonify({
            "msg": f"El usuario ya tiene un token activo en otro dispositivo ({existing_token['device_id']})",
            "code": "USER_ALREADY_HAS_TOKEN"
        }), 409

    else:
        # Primer login → nuevo jti
        jti = str(uuid4())
        access_token, refresh_token = auth_service.generate_tokens({
            "username": user_model.username,
            "rol": user_model.rol,
            "device_id": device_id,
            "jti": jti
        })

        # Guardar refresh token
        upsert_ok = auth_service.upsert_new_token(
            username=user_model.username,
            device_id=device_id,
            refresh_token=refresh_token,
            jti=jti,
            ip_address=ip_address,
            browser=browser,
            os=so,
            refresh_attempts=0
        )
        if not upsert_ok.get("success"):
            return jsonify({"msg": upsert_ok.get("message"), "code": "UPSERT_TOKEN_FAILED"}), 500

    # 6️⃣ Crear o actualizar sesión
    user_model_session = UserSessionModel(
        user_id=user_model.id,
        device_id=device_id,
        ip_address=ip_address,
        browser=browser,
        os=so,
        login_at=update_datetime_format_iso(datetime.datetime.now(tz=timezone.utc)),
        refresh_token=refresh_token,
        last_refresh_at=update_datetime_format_iso(datetime.datetime.now(tz=timezone.utc)),
        reason="login",
        role="User"
    )

    usuario_existe: UserSessionModel = existe_usuario(user_model_session.user_id)
    if usuario_existe is None:
        insert_result = session_service.register_session(user_session=user_model_session)
        if not insert_result.get("success"):
            return jsonify({"msg": insert_result.get("message"), "code": "REGISTER_SESSION_FAILED"}), 500
    else:
        audit_service.update_session_activity(
            user_id=usuario_existe.user_id,
            ip_address=user_model_session.ip_address,
            user_agent=user_model_session.browser,
            reason="login"
        )

    # 7️⃣ Respuesta
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "device_id": device_id,
        "rol": user_model.rol
    }), 200

@backend_bp.route("/auth/refresh", methods=["POST"])
@jwt_required_custom
def refresh(user):
    user_service = UserService()
    auth_service = AuthService()
    session_service = SessionService()
    audit_service = AuditService()
    data = request.get_json()
    
    if not data:
        return jsonify({"msg": "JSON inválido o vacío", "code": "INVALID_JSON"}), 400

    refresh_token = data.get("refresh_token")
    device_id = str(data.get("device_id", "")).strip()
    user_agent = data.get("user_agent", {})
    browser, so = user_agent.get("browser"), user_agent.get("os")
    ip = request.remote_addr

    if not refresh_token or not device_id:
        return jsonify({"msg": "Faltan datos requeridos", "code": "MISSING_FIELDS"}), 400

 
    # Verificar existencia del refresh en DB
    stored = auth_service.get_refresh_token_from_db(refresh_token)
    if not stored:
        return jsonify({"msg": "Token no válido. Iniciá sesión nuevamente.", "code": "InvalidTokenError"}), 401

    ic("DEVICE_REQ",device_id)

    # Validar que está en uso, no expirado y coincide con device
    in_use = auth_service.get_active_token_by_user_and_device(username=stored["username"], device_id=device_id)
    if not in_use:
        return jsonify({"msg": "Dispositivo no coincide", "code": "DeviceMismatch"}), 403

    # Validar revocado o intentos máximos
    if stored.get("revoked_at"):
        return jsonify({"msg": "Token revocado", "code": "RevokedToken"}), 401

    if stored.get("refresh_attempts", 0) >= 2:
        return jsonify({"msg": "Se alcanzó el máximo de intentos de refresh", "code": "MaxAttemptsExceeded"}), 403

    # Verificar firma y expiración
    payload = auth_service.get_token_payload(token=refresh_token)
    if auth_service.is_token_expired(exp=float(payload["exp"])):
        return jsonify({"msg": "Token expirado", "code": "Expired"}), 401

    username, jti = payload["sub"], payload["jti"] # 🔑 Mantener jti del refresh

    revocar_old_token = auth_service.revoke_old_token(username=username,device_id=device_id,token=refresh_token)
    if not revocar_old_token.get("success"):
        return jsonify({"msg": revocar_old_token.get("message"), "code": "REVOKED_OLD_TOKEN_FAILED"}), 500
    # Generar nuevos tokens respetando el jti
    access_token, new_refresh_token = auth_service.generate_tokens({
        "username": username,
        "jti": jti,
        "device_id": device_id,
        "rol": payload["rol"]
    })

    # Persistir nuevo refresh token
    attempts = stored.get("refresh_attempts", 0) + 1
    upsert_new_token = auth_service.upsert_new_token(
        username=username,
        device_id=device_id,
        jti=jti,
        refresh_token=new_refresh_token,
        browser=browser,
        os=so,
        ip_address=ip,
        refresh_attempts=attempts
    )
    if not upsert_new_token.get("success"):
        return jsonify({"msg": upsert_new_token.get("message"), "code": "UPSERT_TOKEN_FAILED"}), 500

    user_model: UserModel = user_service.get_user_by_username(username=username)
    if user_model is None:
            return jsonify({"msg": "No existe usuario para refrescar token", "code": "INVALID_USER_TOKEN"}), 500
    else:
        user_sesion = session_service.update_session(user_id=ObjectId(user_model.id), token=new_refresh_token, reason="refresh_token")
        if not user_sesion.get("success"):
            return jsonify({"msg": "Problemas al actualizar session del usuario", "code": "INVALID_UPDATE_USER"}), 500
        # Crear o actualizar sesión
        audit_service.update_session_activity(
            user_id=user_model.id,
            ip_address=ip,
            user_agent=browser,
            reason="refresh_token"
        )


    # Responder con tokens actualizados
    decoded = auth_service.get_token_payload(new_refresh_token)
    return jsonify({
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "device_id": decoded["device_id"],
        "username": decoded["username"],
        "rol": decoded["rol"],
        "exp": decoded["exp"]
    }), 200

@backend_bp.route("/auth/dashboard", methods=["GET"])
@jwt_required_custom
def dashboard(user):
    ic("DASHBOARD",user)

    if "error" in user:
         return jsonify({"message": user.get("message"), "code": user.get("code")}), 400

    return jsonify({
        "username": user["sub"],
        "rol": user["rol"],
        "device_id": user["device_id"],
        "exp": user["exp"],
        "jti": user["jti"]
    }),200

@backend_bp.route("/auth/logout", methods=["POST"])
@jwt_required_custom
def logout(user):
    user_service = UserService()
    session_service = SessionService()
    audit_service = AuditService()
    auth_service = AuthService()
    blacklist_service = TokenBlacklistService()
    audit_service = AuditService()
    data = request.get_json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    device_id = data.get("device_id")
    reason = data.get("reason")
    user_agent = data.get("user_agent", {})
    browser, so = user_agent.get("browser"), user_agent.get("os")
    client_ip = request.remote_addr

    try:

        username = user.get("username")

        # 🔐 Marcar refresh_token como revocado
        update_revoked_token = auth_service.revoke_old_token(username=username,device_id=device_id,token=refresh_token)
        if not update_revoked_token.get("success"):
            return jsonify({"msg": update_revoked_token.get("message"), "code": "INVALID_REVOKED_TOKEN"})
        # 🔒 Revocar access_token
        update_revoked_token_blacklist = blacklist_service.revoke_token_blacklist(token=access_token,device_id=device_id, username=username,reason=reason)
        if not update_revoked_token_blacklist.get("success"):
            return jsonify({"msg": update_revoked_token_blacklist.get("message"), "code": "INVALID_REVOKED_TOKEN_BLACKLIST"})
        # 📝 Log opcional (auditoría)
        
        user_model: UserModel = user_service.get_user_by_username(username=username)
        user_sesion = audit_service.update_session_activity(
            user_id=user_model.id,
            ip_address=client_ip,
            user_agent=browser,
            reason=reason
        )
        
        if not user_sesion.get("success"):
            return jsonify({"msg": user_sesion.get("message"), "code": "INVALID_SESSION_CLOSED"})
        # Crear o actualizar sesión
        

        ic(f"🔒 Logout: {username} desde IP {client_ip} usando device_id {device_id}")

        return jsonify({"msg": "Sesion Cerrada con exito", "code": "LOGOUT"}), 200

    except Exception as e:
        ic(f"❌ Error en logout: {str(e)}")
        return jsonify({"msg": f"Token inválido o sesión corrupta: {str(e)}"}), 400


@backend_bp.route("/auth/close", methods=["POST"])
@jwt_required_custom
def close(user):
    user_service = UserService()
    session_service = SessionService()
    audit_service = AuditService()
    auth_service = AuthService()
    blacklist_service = TokenBlacklistService()
    audit_service = AuditService()
    try:
        # Detectar si viene JSON o raw body
        data = {}
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            # `sendBeacon` a veces manda como text/plain
            raw = request.data.decode("utf-8")
            try:
                import json
                data = json.loads(raw)
            except Exception:
                data = {"raw": raw}

        ic(f"🔑 Logout recibido: {data}")
        username = user.get("username")
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        device_id = data.get("device_id")
        reason = data.get("reason")
        user_agent = data.get("user_agent", {})
        browser, so = user_agent.get("browser"), user_agent.get("os")
        client_ip = request.remote_addr

        # 👉 Aquí llamas a tu TokenBlacklistService o DbManager para invalidar
        if refresh_token:
            # 🔐 Marcar refresh_token como revocado
            update_revoked_token = auth_service.revoke_old_token(username=username,device_id=device_id,token=refresh_token)
            if not update_revoked_token.get("success"):
                return jsonify({"msg": update_revoked_token.get("message"), "code": "INVALID_REVOKED_TOKEN"})
             # 🔒 Revocar access_token
            update_revoked_token_blacklist = blacklist_service.revoke_token_blacklist(token=access_token,device_id=device_id, username=username,reason=reason)
            if not update_revoked_token_blacklist.get("success"):
                return jsonify({"msg": update_revoked_token_blacklist.get("message"), "code": "INVALID_REVOKED_TOKEN_BLACKLIST"})
            user_model: UserModel = user_service.get_user_by_username(username=username)
            user_sesion = session_service.update_session(user_id=ObjectId(user_model.id), token=refresh_token, reason=reason)
            if not user_sesion.get("success"):
                return jsonify({"msg": user_sesion.get("message"), "code": "INVALID_SESSION_CLOSED"})

            # Crear o actualizar sesión
            audit_service.update_session_activity(
                user_id=user_model.id,
                ip_address=client_ip,
                user_agent=browser,
                reason="close"
            )

        return jsonify({
            "msg": f"Sesión cerrada ({reason})",
            "timestamp": datetime.datetime.now(timezone.utc).isoformat()
        }), 200

    except Exception as e:
        return jsonify({"msg": f"Error al procesar logout: {str(e)}"}), 500