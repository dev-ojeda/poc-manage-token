from flask import Blueprint, request
from app.logging_config import get_logger
from app.midleware.jwt_guard import jwt_user_required, log_endpoint
from app.helpers.helpers import json_response
from app.auth import get_auth_services

logger = get_logger("ENDPOINTS_WEBAUTHN")
services = get_auth_services()
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/me", methods=["GET"])
@jwt_user_required
@log_endpoint
def get_me(user):
    """Devuelve información del usuario autenticado"""
    user_info = services.user_service.get_user_by_username(user.sub)
    if not user_info:
        return json_response(False, "Usuario no encontrado", "USER_NOT_FOUND", 404)
    return json_response(True, "Usuario autenticado", "USER_OK", 200, data={
        "username": user_info.username,
        "role": getattr(user_info, "rol", "user"),
        "user_id": str(user_info._id),
    })


# @auth_bp.route("/refresh", methods=["POST"])
# @log_endpoint
# def refresh_token():
#     """Renueva access_token usando refresh_token"""
#     data = request.get_json(silent=True) or {}
#     refresh_token = data.get("refresh_token")

#     if not refresh_token:
#         return json_response(False, "Refresh token requerido", "REFRESH_REQUIRED", 400)

#     token_doc = services.auth_service.get_token_payload(token=refresh_token, expected_type="refresh")
#     if not token_doc:
#         return json_response(False, "Token inválido", "TOKEN_INVALID", 401)

#     if services.auth_service.is_token_expired(token_doc.exp):
#         return json_response(False, "Token expirado", "TOKEN_EXPIRED", 401)

#     new_tokens = services.auth_service.refresh_access_token(token_doc)
#     return json_response(True, "Token renovado", "TOKEN_REFRESHED", 200, data=new_tokens)
