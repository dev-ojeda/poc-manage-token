#!/usr/bin/env python
# -*- coding: utf-8 -*-

# middlewares/jwt_guard.py

from functools import wraps
from flask import request, jsonify, g
from app.auth.services.auth_service import AuthService
from app.auth.services.user_service import UserService

from app.hekpers.token_doc import TokenDoc
from app.model.user_model import UserModel

auth_service = AuthService()

def decode_token_from_header(expected_type="access"):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, {"msg": "Token no enviado", "code": "TOKEN_NOT_FOUND"}
    
    token = auth.replace("Bearer ", "")
    decoded: TokenDoc = auth_service.get_token_payload(token=token, expected_type=expected_type)

    if "error" in decoded:
        return None, decoded

    # 🚨 Validar expiración
    if auth_service.is_token_expired(decoded.get("exp", 0)):
        return None, {"msg": "Token expirado", "code": "TOKEN_EXPIRED"}

    # 🚨 Validar en DB si está en uso / revocado
    username = decoded.get("sub")
    jti = decoded.get("jti")
    active = auth_service.get_active_token_by_username(username)

    if not active:
        return None, {"msg": "Token revocado o inexistente", "code": "TOKEN_REVOKED"}

    # 🚨 Si es refresh, detectar reuso
    if expected_type == "refresh" and auth_service.detect_reuse(active):
        return None, {"msg": "Refresh token ya fue usado", "code": "TOKEN_REUSED"}

    return decoded, None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        public_paths = ["/auth", "/static", "/favicon.ico"]
        if any(request.path.startswith(p) for p in public_paths):
            return f(*args, **kwargs)

        decoded, error = decode_token_from_header(
            expected_type=request.headers.get("X-Token-Type", "access")
        )
        if error:
            return jsonify(error), 401

        username = decoded.get("sub")
        user_service = UserService()
        user: UserModel = user_service.get_user_by_username(username=username)
        if not user or user.rol != "Admin":
            return jsonify({"msg": "⛔ Acceso denegado: se requiere rol Admin"}), 403

        g.user = decoded
        return f(decoded, *args, **kwargs)
    return decorated_function


def jwt_required_custom(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        public_paths = ["/auth", "/static", "/favicon.ico"]
        if any(request.path.startswith(p) for p in public_paths):
            return f(*args, **kwargs)
        
        decoded, error = decode_token_from_header(expected_type=request.headers.get("X-Token-Type"))
        if error:
            return jsonify(error), 401
        return f(*args,user=decoded, **kwargs)
    
    return decorated_function
