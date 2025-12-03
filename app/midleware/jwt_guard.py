# app/middlewares/jwt_guard.py
import time
from collections import defaultdict
from functools import wraps
from typing import Optional, Tuple, Callable, Any
from flask import request, g
from app.auth import get_auth_services
from app.logging_config import get_logger
from app.helpers.helpers import is_ignored, json_response
from app.model.token_model import TokenModel

# === Inicialización única ===
services = get_auth_services()
logger = get_logger("JWT_GUARD")

# === Rate limiting en memoria (usar Redis en prod) ===
RATE_LIMIT_STORE = defaultdict(list)
RATE_LIMIT_CONFIG = {
    "user": {"limit": 30, "window": 60},   # 30 req/min por usuario
    "ip":   {"limit": 100, "window": 60},  # 100 req/min por IP
}


def decode_token_from_header(expected_type: str = "access") -> Tuple[Optional[TokenModel], Optional[Any]]:
    """Decodifica y valida el token JWT desde el header Authorization."""
    auth: str = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        logger.warning("Token no enviado - TOKEN_NOT_FOUND")
        return None, json_response(False, "Token no enviado", "TOKEN_NOT_FOUND", 401)

    token: str = auth.removeprefix("Bearer ").strip()
    token_doc = services.auth_service.get_token_payload(token=token, expected_type=expected_type)
    if not token_doc:
        logger.warning("Token inválido - TOKEN_INVALID")
        return None, json_response(False, "Token inválido", "TOKEN_INVALID", 401)

    if services.auth_service.is_token_expired(token_doc.exp):
        logger.warning("Token expirado - TOKEN_EXPIRED")
        return None, json_response(False, "Token expirado", "TOKEN_EXPIRED", 401)

    active_resp = services.auth_service.get_active_token_by_username(token_doc.sub)
    if not active_resp.get("success"):
        logger.warning("Token revocado o inexistente - TOKEN_REVOKED")
        return None, json_response(False, "Token revocado o inexistente", "TOKEN_REVOKED", 401)

    if expected_type == "refresh" and services.auth_service.detect_reuse(active_resp.get("data")):
        logger.warning("Refresh token reutilizado - TOKEN_REUSED")
        return None, json_response(False, "Refresh token reutilizado", "TOKEN_REUSED", 401)

    return token_doc, None


def jwt_admin_required(f: Callable) -> Callable:
    """Protege endpoints que requieren rol Admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        public = ["/auth", "/static", "/favicon.ico"]
        if any(request.path.startswith(p) for p in public):
            return f(*args, **kwargs)

        token_doc, error = decode_token_from_header(request.headers.get("X-Token-Type", "access"))
        if error:
            return error

        user_resp = services.user_service.get_user_by_username(token_doc.sub)
        if not user_resp or getattr(user_resp.rol, "rol", None) != "Admin":
            logger.warning("Acceso denegado: requiere rol Admin")
            return json_response(False, "Acceso denegado: requiere rol Admin", "ACCESS_DENIED", 403)

        g.user = token_doc
        return f(user=token_doc, *args, **kwargs)
    return decorated


def jwt_user_required(f: Callable) -> Callable:
    """Protege endpoints que requieren token de usuario."""
    @wraps(f)
    def decorated(*args, **kwargs):
        public = ["/auth", "/static", "/favicon.ico"]
        if any(request.path.startswith(p) for p in public):
            return f(*args, **kwargs)

        token_doc, error = decode_token_from_header(request.headers.get("X-Token-Type", "access"))
        if error:
            return error

        g.user = token_doc
        return f(user=token_doc, *args, **kwargs)
    return decorated


def log_endpoint(fn: Callable) -> Callable:
    """Loguea entrada y salida de endpoints."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        logger.info(f"➡️ {fn.__name__} | {request.method} {request.path}")
        try:
            resp = fn(*args, **kwargs)
            logger.info(f"✅ {fn.__name__} completado en {round(time.perf_counter() - start, 3)}s")
            return resp
        except Exception as e:
            logger.exception(f"💥 {fn.__name__} falló: {e}")
            return json_response(False, "Error interno del servidor", "INTERNAL_ERROR", 500)
    return wrapper


def metrics_endpoint(fn: Callable) -> Callable:
    """Registra métricas internas de duración."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        resp = fn(*args, **kwargs)
        dur = (time.perf_counter() - start) * 1000
        if not is_ignored(request.path):
            status = resp[1] if isinstance(resp, tuple) else 200
            logger.info(f"📊 {fn.__name__} -> {round(dur, 2)}ms | {status}")
        return resp
    return wrapper


def rate_limit(fn: Callable) -> Callable:
    """Limitador de tasa simple por IP o usuario."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = getattr(g, "user", None)
        if user_id:
            key = f"user:{getattr(user_id, 'sub', None)}"
            cfg = RATE_LIMIT_CONFIG["user"]
        else:
            key = f"ip:{request.remote_addr}"
            cfg = RATE_LIMIT_CONFIG["ip"]

        now = time.time()
        RATE_LIMIT_STORE[key] = [t for t in RATE_LIMIT_STORE[key] if now - t < cfg["window"]]

        if len(RATE_LIMIT_STORE[key]) >= cfg["limit"]:
            logger.warning(f"Rate limit excedido -> {key}")
            return json_response(False, "Demasiadas solicitudes", "RATE_LIMIT_EXCEEDED", 429)

        RATE_LIMIT_STORE[key].append(now)
        return fn(*args, **kwargs)
    return wrapper
