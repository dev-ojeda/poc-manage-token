#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from pickle import FLOAT
from bson import ObjectId
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv
from icecream import ic

from auth.services.session_service import SessionService
from auth.services.user_service import UserService
from dao.user_dao import UserDAO
from utils.db_manager import DbManager
from midleware.jwt_guard import admin_required, log_refresh_attempt
from model.token_generator import TokenGenerator
from model.user import User


load_dotenv()
admin_bp = Blueprint("admin_bp", __name__)

@admin_bp.route("/auth/admin", methods=["POST"])
@log_refresh_attempt
def login():
    us = UserService()
    data = request.get_json()
    user_agent = data.get("user_agent")
    ip_address = request.remote_addr
    if not request.is_json:
        return jsonify({"msg": "Content-Type debe ser application/json", "code": "INVALID_JSON"}), 400

    missing = us.validate_login_payload(data)
    if missing:
        return jsonify({"msg": f"Faltan campos: {', '.join(missing)}", "code": "MISSING_FIELDS"}), 400

    tg = TokenGenerator()
    user_model_dao = UserDAO()

    user_model = user_model_dao.find_by_username(username=data.get("username"))
    if not user_model:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    # if not User.verify_password(data["password"], user_model.password):
    #     return jsonify({"msg": "Credenciales incorrectas", "code": "INVALID_CREDENTIALS"}), 401
    
    access_token, refresh_token = tg.create_tokens({
        "username": user_model.username,
        "jti": None,
        "device_id": data["device"],
        "rol": user_model.rol
    })

    decoded = tg.verify_token(access_token, expected_type="access")
    
    validate_upsert_user_token = us.persist_refresh_token_admin(decoded, refresh_token, user_agent, ip_address)
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
@log_refresh_attempt
def dashboard(user):
    return jsonify({
        "username": user.get("username"),
        "rol": user.get("rol"),
        "device_id": user.get("device_id"),
        "exp": user.get("exp"),
        "jti": user.get("jti")
    }),200

@admin_bp.route("/admin/audit", methods=["POST"])
@admin_required
@log_refresh_attempt
def get_audit_logs():
    data = request.get_json()
    if not request.is_json:
        return jsonify({"msg": "Content-Type debe ser application/json"}), 400

    username = data.get("username")
    dm = DbManager()

    filtro = {
        "username": username,
    }

    start = data.get("start")
    end = data.get("end")

    if start:
        filtro["timestamp"] = {"$gte": datetime.fromtimestamp(float(start), tz=timezone.utc)}
    if end:
        filtro.setdefault("timestamp", {})["$lte"] = datetime.fromtimestamp(float(end), tz=timezone.utc)

    projection = {
        "_id": 0,
        "username": 1,
        "ip_address": 1,
        "user_agent": 1,
        "previous_ip": 1,
        "previous_ua": 1,
        "reason": 1,
        "timestamp": 1
    }

    logs = list(dm.conexion.find(dm.session_audit, filtro, projection).sort("timestamp", -1))
    return jsonify({"logs": logs}), 200

@admin_bp.route('/auth/sessions/active', methods=['POST'])
@admin_required
@log_refresh_attempt
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
        
        ic(f"[filtro_status]: {filtro_status}")   
        # Obtenemos los IDs de usuarios que no son Admin
        sessions = SessionService.get_non_admin_active_sessions(filtro_status=filtro_status)
        
        # user_ids = [user["_id"] for user in non_admin_users]
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

        ic(f"[SESSION SERVICE]: {result}")    
        return jsonify({"count": len(result), "sessions": result})

    except Exception as e:
        ic(e)
        return jsonify({"msg": f"❌ Error al obtener sesiones: {str(e)}"}), 500

@admin_bp.route("/auth/sessions/revoke", methods=["POST"])
@admin_required
def revoke_session(user):
    dm = DbManager()
    data = request.json;
    token_type = request.headers.get("X-Token-Type")
    session_id = data.get("user_id")
    username = data.get("username")
    device_id = data.get("device_id")
    user_rol = data.get("user_rol")
    refreshToken = data.get("refresh_token")
    if user_rol == user.get("rol"):
        return jsonify({"msg": "Username diferente"}), 400
    if device_id == user.get("device_id"):
        return jsonify({"msg": "Device diferente"}), 400

    if token_type != "refresh":
        return jsonify({"msg": "Token diferente"}), 400

    result = dm.revoke_refresh_token(username=username, device_id=device_id, refresh_token=refreshToken)
    if not result.get("success"):
        return jsonify({"msg": result.get("message"), "code": "INVALID_REVOCKED_REFRESH_TOKEM"})

    ss = SessionService()
    result_revocar = ss.revoke_session(user_id=ObjectId(session_id))
    if not result_revocar.get("success"):
        return jsonify({"msg": result_revocar.get("message"), "code": "INVALID_REVOCKED"})
    return jsonify({"msg": "Sesión revocada"}), 200
