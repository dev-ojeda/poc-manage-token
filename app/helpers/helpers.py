# -----------------------
# Helpers
# -----------------------
import base64
import datetime
from logging import Logger

from flask import jsonify, request
from flask.globals import g

IGNORED_PATHS = [
    "/health",
    "/static",
    "/favicon.ico",
    "/.well-known/appspecific/com.chrome.devtools.json",
]

def iso_now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)

def json_response(success: bool, message: str, code: str, status: int = 200, **extra):
    """Formato de respuesta consistente."""
    base = {"success": success, "msg": message, "code": code, "status": status}
    base.update(extra)
    return jsonify(base), status

def get_request_data():
    if not request.is_json:
        return None, json_response(False, "Content-Type debe ser application/json", "INVALID_JSON", 400)
    return request.get_json(silent=True) or {}, None

def get_user_agent_info(user_agent: dict):
    return user_agent.get("browser"), user_agent.get("os")


def is_ignored(path: str) -> bool:
    """Revisa si el path debe excluirse de métricas y logging."""
    return any(path == p or path.startswith(p + "/") for p in IGNORED_PATHS)

# =========================================================
# 🔍 UTILIDADES DE LOGGING
# =========================================================
def get_request_context():
    """Obtiene información contextual de la request actual."""
    try:
        return {
            "path": request.path,
            "ip": request.remote_addr or "127.0.0.1",
            "method": request.method,
            "user": getattr(g, "user", {}).get("sub", "anonymous")
        }
    except RuntimeError:
        return {"path": "N/A", "ip": "N/A", "method": "N/A", "user": "N/A"}

def log_and_response(success, message, code, status, logger: Logger, level="error"):
    """Centraliza log + respuesta JSON estructurada."""
    ctx = get_request_context()
    log_data = {**ctx, "code": code, "message": message}
    getattr(logger, level)(log_data)
    return json_response(success, message, code, status)

def b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def b64u_decode(data: str) -> bytes:
    pad = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + pad)