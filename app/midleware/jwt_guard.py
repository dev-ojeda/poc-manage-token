#!/usr/bin/env python
# -*- coding: utf-8 -*-

# middlewares/jwt_guard.py

from datetime import datetime, timezone
from functools import wraps
from flask import redirect, request, jsonify, g, url_for
from icecream import ic
from auth.services.user_service import UserService

from model.token_generator import TokenGenerator
from utils.db_manager import DbManager  # Asegúrate que esta clase maneje verificación JWT

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"msg": "🔒 Token no proporcionado"}), 401

        token = auth_header.replace("Bearer ", "")
        tg = TokenGenerator()
        decoded = tg.verify_token(token=token)
        if "error" in decoded:
            return jsonify({"msg": decoded.get("error"), "code": decoded.get("code")}), 401
        us = UserService()
        username = decoded.get("sub")
        user = us.get_user_by_username(username=username)
        if not user or user.rol != "Admin":
            return jsonify({"msg": "⛔ Acceso denegado: se requiere rol Admin"}), 403

        # inyectamos usuario al contexto si se necesita
        request.user = decoded
        return f(user=decoded, *args, **kwargs)
    return decorated_function

def jwt_required(token_generator: TokenGenerator, expected_type="access"):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            public_paths = ["/auth", "/static", "/favicon.ico"]
            if any(request.path.startswith(p) for p in public_paths):
                return f(*args, **kwargs)
            auth = request.headers.get("Authorization", "")
            token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else None
            if not token:
                return jsonify({"msg": "Token no enviado"}), 401
            try:
                payload = token_generator.verify_token(token, expected_type=expected_type)
                g.jwt_payload = payload
            except Exception as e:
                return jsonify({"msg": f"Error inesperado: {str(e)}"}), 400

            return f(*args, **kwargs)
        return wrapper
    return decorator

def jwt_required_app(token_generator: TokenGenerator, expected_type="access"):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            public_paths = ["/auth", "/static", "/favicon.ico"]
            if any(request.path.startswith(p) for p in public_paths):
                return f(*args, **kwargs)
            auth = request.headers.get("Authorization", "")
            token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else None
            if not token:
                return jsonify({"msg": "Token no enviado"}), 401
            try:
                payload = token_generator.verify_token_global(token, expected_type=expected_type)
                g.jwt_payload = payload
            except Exception as e:
                return jsonify({"msg": f"Error inesperado: {str(e)}"}), 400

            return f(*args, **kwargs)
        return wrapper
    return decorator

def jwt_required_global(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        public_paths = ["/auth", "/static", "/favicon.ico"]
        if any(request.path.startswith(p) for p in public_paths):
            return f(*args, **kwargs)
        try:
            dm = DbManager()
            tg = TokenGenerator()
            token = dm.exists_token_global()
            if not token:
                return jsonify({'msg': 'Token no existe'}), 401
            decoded = tg.verify_token_global(token=token.get("token"), expected_type="access")
            g.user_app = decoded
        except Exception as ex:
            return jsonify({"msg": f"Error interno al verificar token: {ex}"}), 500

        return f(*args, **kwargs)
    return decorated_function

def jwt_required_custom(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        public_paths = ["/auth", "/static", "/favicon.ico"]
        if any(request.path.startswith(p) for p in public_paths):
            return f(*args, **kwargs)
        auth = request.headers.get("Authorization", "")
        token_type = request.headers.get("X-Token-Type")
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else None
        if not token:
            return jsonify({"msg": "Token no enviado", "code": "TOKEN_NOT_FOUND"}),401
        try:
            tg = TokenGenerator()
            payload = tg.verify_token(token=token,expected_type=token_type)
            g.user = payload
        except Exception as e:
                return jsonify({"msg": f"Error inesperado: {str(e)}"}), 400
        return f(payload, *args, **kwargs)
    return decorated_function

def jwt_required_custom_refresh(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization", None)
        tipo = request.headers.get("X-Token-Type", None)
        if not auth or not auth.startswith("Bearer "):
            return redirect(url_for('frontend.index') + '?untoken=true')
            # return jsonify({"msg": "Token faltante o inválido"}), 401
        token_refresh = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else None
        tg = TokenGenerator()
        payload = tg.verify_token(token=token_refresh,expected_type=tipo)
        return f(user=payload,user_token_refresh=token_refresh, *args, **kwargs)
    return decorated_function

def log_refresh_attempt(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        request_id = f"{datetime.now(timezone.utc).isoformat()}-{request.remote_addr}/{request.path}"
        sec = request.is_secure
        ic(f"[ATTEMPT] SECURE: {sec} - REQUEST_ID: {request_id}")
        return f(*args, **kwargs)
    return wrapper