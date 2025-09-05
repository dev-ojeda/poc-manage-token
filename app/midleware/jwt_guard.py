#!/usr/bin/env python
# -*- coding: utf-8 -*-

# middlewares/jwt_guard.py

from datetime import datetime, timezone
from functools import wraps
import logging
from flask import request, jsonify, g
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pymongo.errors import PyMongoError
from app.auth import UserService

from app.model import TokenGeneratorModel, UserModel
from app.utils.db_manager import DbManager  # Asegúrate que esta clase maneje verificación JWT


def decode_token_from_header(expected_type="access"):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, {"msg": "Token no enviado", "code": "TOKEN_NOT_FOUND"}
    token = auth.replace("Bearer ", "")
    tgm = TokenGeneratorModel()
    decoded = tgm.verify_token(token=token, expected_type=expected_type)
    if "error" in decoded:
        return None, decoded
    return decoded, None

# def admin_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         auth_header = request.headers.get("Authorization", "")
#         if not auth_header.startswith("Bearer "):
#             return jsonify({"msg": "🔒 Token no proporcionado"}), 401
#         token = auth_header.replace("Bearer ", "")
#         tipo = request.headers.get("X-Token-Type","")
#         token_generator_model = TokenGeneratorModel()
#         decoded = token_generator_model.verify_token(token=token,expected_type=tipo)
#         if "error" in decoded:
#             return jsonify({"msg": decoded.get("error"), "code": decoded.get("code")}), 401
#         username = decoded.get("sub")
#         user_service = UserService()
#         user: UserModel = user_service.get_user_by_username(username=username)
#         if not user or user.rol != "Admin":
#             return jsonify({"msg": "⛔ Acceso denegado: se requiere rol Admin"}), 403

#         # inyectamos usuario al contexto si se necesita
#         request.user = decoded
#         return f(user=decoded, *args, **kwargs)
#     return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        public_paths = ["/auth", "/static", "/favicon.ico"]
        if any(request.path.startswith(p) for p in public_paths):
            return f(*args, **kwargs)

        decoded, error = decode_token_from_header(expected_type=request.headers.get("X-Token-Type"))
        if error:
            return jsonify(error), 401

        username = decoded.get("sub")
        user_service = UserService()
        user: UserModel = user_service.get_user_by_username(username=username)
        if not user or user.rol != "Admin":
            return jsonify({"msg": "⛔ Acceso denegado: se requiere rol Admin"}), 403

         # inyectamos usuario al contexto si se necesita
        g.user = decoded
        return f(decoded, *args, **kwargs)

    return decorated_function


def jwt_required_global(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        public_paths = ["/auth", "/static", "/favicon.ico"]
        if any(request.path.startswith(p) for p in public_paths):
            return f(*args, **kwargs)
        try:
            dm = DbManager()
            token = dm.exists_token_global()
            if not token:
                return jsonify({'msg': 'Token no existe'}), 401
            token_generator_model = TokenGeneratorModel()
            decoded = token_generator_model.verify_token_global(token=token.get("token"), expected_type="access")
            g.user_app = decoded
        except PyMongoError as ex:
            return jsonify({"msg": f"Error de base de datos: {ex}"}), 500
        except ExpiredSignatureError:
            return jsonify({"msg": "El token ha expirado"}), 401
        except InvalidTokenError as ex:
            return jsonify({"msg": f"Token inválido: {ex}"}), 401

        return f(*args, **kwargs)
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
        
        g.user = decoded
        return f(decoded, *args, **kwargs)
    
    return decorated_function

def jwt_required_custom_refresh(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization", None)
        tipo = request.headers.get("X-Token-Type", None)
        if not auth or not auth.startswith("Bearer "):
            return jsonify({"msg": "Token no enviado", "code": "TOKEN_NOT_FOUND"}),401
            # return jsonify({"msg": "Token faltante o inválido"}), 401
        token_refresh = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else None
        token_generator_model = TokenGeneratorModel()
        payload = token_generator_model.verify_token(token=token_refresh,expected_type=tipo)
        return f(user=payload,user_token_refresh=token_refresh, *args, **kwargs)
    return decorated_function

def log_refresh_attempt(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        request_id = f"{datetime.now(timezone.utc).isoformat()}-{request.remote_addr}/{request.path}"
        logger = logging.getLogger("audit")
        logger.info(f"[ATTEMPT] SECURE: {request.is_secure} - REQUEST_ID: {request_id}")
        return f(*args, **kwargs)
    return wrapper