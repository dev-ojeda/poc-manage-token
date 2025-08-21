#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from uuid import uuid4
from bson import ObjectId
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv
from icecream import ic

from app.auth.services.audit_service import AuditService
from app.auth.services.auth_service import AuthService
from app.web_socket.event_socket import notificar_revocacion
from app.auth.services.session_service import SessionService
from app.auth.services.user_service import UserService
from app.dao.user_dao import UserDAO
from app.utils.db_manager import DbManager
from app.midleware.jwt_guard import admin_required
from app.model.token_generator import TokenGenerator


load_dotenv()
admin_bp = Blueprint("admin_bp", __name__)

@admin_bp.route("/auth/admin", methods=["POST"])
def login():
    user_service = UserService()
    auth_service = AuthService()
    data = request.get_json()
    user_agent = data.get("user_agent", {})
    browser, so = user_agent.get("browser"), user_agent.get("os")
    ip_address, device_id = request.remote_addr, data.get("device")
    if not request.is_json:
        return jsonify({"msg": "Content-Type debe ser application/json", "code": "INVALID_JSON"}), 400

    missing = user_service.validate_login_payload(data)
    if missing:
        return jsonify({"msg": f"Faltan campos: {', '.join(missing)}", "code": "MISSING_FIELDS"}), 400

    tg = TokenGenerator()
    user_model_dao = UserDAO()

    user_model = user_model_dao.find_by_username(username=data.get("username"))
    if not user_model:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    # if not User.verify_password(data["password"], user_model.password):
    #     return jsonify({"msg": "Credenciales incorrectas", "code": "INVALID_CREDENTIALS"}), 401

    existing_token = auth_service.is_token_in_use(user_model.username)
    if existing_token and existing_token["device_id"] == data.get("device_id"):
        if auth_service.is_token_expired(exp=float(existing_token["expires_at"].timestamp())):
            # Token expirado → nuevo jti y tokens
            jti = str(uuid4())
            access_token, refresh_token = auth_service.generate_tokens({
                "username": user_model.username,
                "rol": user_model.rol,
                "device_id": data.get("device_id"),
                "jti": jti
            })
            # Guardar refresh token
            upsert_ok = auth_service.upsert_new_token(
                username=user_model.username,
                device_id=data.get("device_id"),
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

    decoded = tg.verify_token(access_token, expected_type="access")
    
    validate_upsert_user_token = user_service.persist_refresh_token_admin(decoded, refresh_token, user_agent, ip_address)
    if not validate_upsert_user_token.get("success"):
        return jsonify({"msg": validate_upsert_user_token.get("message"), "code": "INVALID_UPSERT_TOKENS"})

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "device_id": decoded.get("device_id"),
        "rol": user_model.rol
    }), 200

@admin_bp.route("/auth/admin/dashboard", methods=["GET"])
@admin_required
def dashboard(user):
    return jsonify({
        "username": user.get("username"),
        "rol": user.get("rol"),
        "device_id": user.get("device_id"),
        "exp": user.get("exp"),
        "jti": user.get("jti")
    }),200

@admin_bp.route("/auth/admin/audit", methods=["POST"])
@admin_required
def get_audit_logs(user):
    """
    Obtener logs de auditoría con filtros opcionales:
    - user_id (str)
    - event_type (str)
    - start (timestamp en segundos)
    - end (timestamp en segundos)
    - page (int)
    - limit (int)
    """
    ads = AuditService()
    try:
        data = request.get_json()
        params = {
            "user_id": data.get("user_id") or None,
            "event_type": data.get("event_type") or None,
            "start": None,
            "end": None,
            "page": int(data.get("page", 1)),
            "limit": int(data.get("limit", 10))
        }

        result = ads.get_logs_audit(**params)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/auth/sessions/active', methods=['POST'])
@admin_required
def get_active_sessions(user):
    """
    Devuelve todas las sesiones activas de usuarios que **no** son Admin.
    Protegido para uso exclusivo de Admins.
    """
    data = request.get_json()
    filtro_status = data.get("filtro_status")
    # dt_at = float(data.get("since_at"))
    # since_dt = datetime.fromtimestamp(dt_at, tz=timezone.utc).isoformat()
    # since_iso = datetime.fromisoformat(since_dt)
    try:
        # Obtenemos los IDs de usuarios que no son Admin
        sessions = SessionService.get_non_admin_active_sessions(filtro_status=filtro_status)
        result = []
        if sessions is not None:
            for session in sessions:
                result.append({
                    "session_id": str(session["session_id"]),
                    "user_id": str(session["user_id"]),
                    "ip_address": session["ip_address"],
                    "browser": session["browser"],
                    "sistena": session["os"],
                    "device_id": session["device_id"],
                    "login_at": int(datetime.fromisoformat(session["login_at"]).timestamp()),
                    "last_refresh_at":int(datetime.fromisoformat(session["last_refresh_at"]).timestamp()),
                    "refresh_token": session["refresh_token"],
                    "is_revoked": session["is_revoked"],
                    "reason": session["reason"],
                    "status": session["status"],
                    "username": session["username"],
                    "rol": session["rol"]
                })
 
        return jsonify({"count": len(result), "sessions": result})

    except Exception as e:
        ic(e)
        return jsonify({"msg": f"❌ Error al obtener sesiones: {str(e)}"}), 500

@admin_bp.route("/auth/sessions/revoke", methods=["POST"])
@admin_required
def revoke_session(user):
    auth_service = AuthService()
    ss = SessionService()
    ads = AuditService()
    data = request.json;
    session_id = data.get("user_id")
    username = data.get("username")
    device_id = data.get("device_id")
    user_rol = data.get("user_rol")
    user_agent = data.get("user_agent")
    refreshToken = data.get("refresh_token")
    ip_address = request.remote_addr
    if user_rol == user.get("rol"):
        return jsonify({"msg": "Username diferente"}), 400
    if device_id == user.get("device_id"):
        return jsonify({"msg": "Device diferente"}), 400


    result = auth_service.revoke_old_token(username=username, device_id=device_id, token=refreshToken)
    if not result.get("success"):
        return jsonify({"msg": result.get("message"), "code": "INVALID_REVOCKED_REFRESH_TOKEM"})
    
    result_revocar = ss.revoke_session(user_id=ObjectId(session_id))
    if not result.get("success"):
         return jsonify({"msg": result.get("message"), "code": "INVALID_REVOCKED_SESSION"})
    validar_operacion = ads.update_session_activity(user_id=ObjectId(session_id),ip_address=ip_address,user_agent=user_agent)
    ic("[VALIDAR_OPERACION]",validar_operacion)
    if not validar_operacion.get("success"):
        return jsonify({"msg": result_revocar.get("message"), "code": "INVALID_REVOCKED"})
    notificar_revocacion(username);
    return jsonify({"msg": "Sesión revocada"}), 200
