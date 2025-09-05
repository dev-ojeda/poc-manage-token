#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import io, csv
from datetime import timezone
from uuid import uuid4
from bson import ObjectId
from flask import Blueprint, jsonify, request, send_file
from dotenv import load_dotenv
from icecream import ic

from app.auth import AuditService, AuthService, SessionService, UserService
from app.dao.format_date import parse_iso8601
from app.web_socket.event_socket import notificar_revocacion
from app.midleware.jwt_guard import admin_required
from app.model import UserModel, TokenGeneratorModel


load_dotenv()
admin_bp = Blueprint("admin_bp", __name__)
# Guardamos métricas en memoria por simplicidad (para producción usar DB)
METRICS = []      # dicts: {type, value, action?, timestamp}

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

    user_model: UserModel = user_service.get_user_by_username(username=data.get("username"))
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

    token_generator_model = TokenGeneratorModel()
    decoded: dict = token_generator_model.verify_token(access_token, expected_type="access")
    
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

    if "error" in user:
         return jsonify({"message": user.get("message"), "code": user.get("code")}), 400

    return jsonify({
        "username": user["sub"],
        "rol": user["rol"],
        "device_id": user["device_id"],
        "exp": user["exp"],
        "jti": user["jti"]
    }),200

@admin_bp.route("/auth/admin/audit", methods=["POST"])
@admin_required
def get_audit_logs(user):
    """
    Obtener logs de auditoría con filtros opcionales:
    - user_id (str, opcional)
    - event_type (str, opcional)
    - start (timestamp en segundos, opcional)
    - end (timestamp en segundos, opcional)
    - page (int, default=1)
    - limit (int, default=10)
    - sort_by (str, opcional: "timestamp", "user_id", "event_type", etc.)
    - direction (str, opcional: "asc" | "desc")
    """
    try:
        audit_service = AuditService()
        result = audit_service.get_all_logs_audit()
        return jsonify({
            "msg": "✅ Logs obtenidos correctamente",
            "code": "SUCCESS",
            "total_count": result.get("total_count", 0),
            "logs": result.get("logs", [])
        }), 200

    except ValueError as ve:
        return jsonify({"msg": str(ve), "code": "VALUE_ERROR"}), 400
    except Exception as e:
        return jsonify({"msg": "❌ Error interno del servidor", "code": "SERVER_ERROR"}), 500

@admin_bp.route("/auth/admin/user", methods=["POST"])
@admin_required
def get_users(user):
    try:
        user_service = UserService()
        result = user_service.get_all_users()
        return jsonify({
            "msg": "✅ users obtenidos correctamente",
            "code": "SUCCESS",
            "total_count": result.get("total_count", 0),
            "logs": result.get("logs", [])
        }), 200

    except ValueError as ve:
        return jsonify({"msg": str(ve), "code": "VALUE_ERROR"}), 400
    except Exception as e:
        return jsonify({"msg": "❌ Error interno del servidor", "code": "SERVER_ERROR"}), 500

@admin_bp.route("/auth/admin/performance", methods=["POST"])
@admin_required
def get_performance(user):
    data = request.get_json()
    return jsonify({
        "data": data
    }),200

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
                    "login_at": parse_iso8601(iso_str=session["login_at"],tz_name="America/Santiago")["timestamp_ms"],
                    "last_refresh_at": parse_iso8601(iso_str=session["last_refresh_at"],tz_name="America/Santiago")["timestamp_ms"],
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
    validar_operacion = ads.update_session_activity(user_id=ObjectId(session_id),ip_address=ip_address,user_agent=user_agent,reason="revoked")
    ic("[VALIDAR_OPERACION]",validar_operacion)
    if not validar_operacion.get("success"):
        return jsonify({"msg": result_revocar.get("message"), "code": "INVALID_REVOCKED"})
    notificar_revocacion(username);
    return jsonify({"msg": "Sesión revocada"}), 200


@admin_bp.route("/auth/metrics/export")
def export_metrics():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp","type","value","action"])
    for m in METRICS:
        writer.writerow([m.get("timestamp",""), m.get("type",""), m.get("value",""), m.get("action","")])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="metrics.csv")


@admin_bp.route("/auth/metrics", methods=["POST"])
def save_metrics():
    ic("METRICS",METRICS)
    data = request.get_json(force=True)
    data["timestamp"] = datetime.datetime.now(tz=timezone.utc)
    METRICS.append(data)
    # Mantener últimas 500 para no crecer infinito
    if len(METRICS) > 500:
        del METRICS[:-500]
    return jsonify(ok=True)

@admin_bp.route("/auth/metrics/latest")
def latest_metrics():
    ic("METRICS",METRICS)
    # Últimas 200 métricas
    return jsonify(METRICS[-200:])