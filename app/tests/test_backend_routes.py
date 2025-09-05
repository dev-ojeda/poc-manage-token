# test_backend.py
import pytest
from bson import ObjectId
from unittest.mock import Mock, patch
from app.backend.routes import existe_usuario

# ===========================
#      FUNCIONES INTERNAS
# ===========================

def test_existe_usuario_none():
    with patch("app.auth.services.session_service.SessionService") as MockSession:
        MockSession.return_value.get_active_session_by_Id.return_value = None
        result = existe_usuario(ObjectId())
        assert result is None

# ===========================
#         ENDPOINTS
# ===========================

def test_logout_override_user(client, auth_headers):
    payload = {"access_token": "a", "refresh_token": "r", "device_id": "d", "reason": "test"}

    with patch("app.auth.services.user_service.UserService.get_user_by_username", return_value=Mock(id="507f1f77bcf86cd799439011")):
        resp = client.post("/auth/logout", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "Sesion Cerrada" in data["msg"]


def test_login_invalid_json(client):
    resp = client.post("/auth/acceso", data="notjson", content_type="text/plain")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "INVALID_JSON"


def test_refresh_missing_fields(client):
    resp = client.post("/auth/refresh", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "MISSING_FIELDS"


def test_refresh_internal_error(client):
    headers = {"Authorization": "Bearer faketoken"}
    with patch("app.auth.services.auth_service.AuthService.get_refresh_token_from_db", side_effect=Exception("DB error")):
        resp = client.post("/auth/refresh", json={"refresh_token": "abc", "device_id": "dev1"}, headers=headers)
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["code"] == "InternalServerError"


def test_logout_success(client, auth_headers, mock_jwt_required):
    payload = {"access_token": "a", "refresh_token": "r", "device_id": "d", "reason": "test"}

    with patch("app.auth.services.user_service.UserService.get_user_by_username", return_value=Mock(id="507f1f77bcf86cd799439011")), \
         patch("app.midleware.jwt_guard.jwt_required_custom", mock_jwt_required):
        resp = client.post("/auth/logout", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "Sesion Cerrada" in data["msg"]


def test_dashboard_ok(client, mock_jwt_required):
    with patch("app.midleware.jwt_guard.jwt_required_custom", mock_jwt_required):
        resp = client.get("/auth/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "neo"
        assert data["rol"] == "Admin"

def test_auth_exception(client):
    resp = client.get("/auth-error")
    data = resp.get_json()
    assert resp.status_code == 401
    assert data["code"] == "InvalidToken"
    assert data["message"] == "Token inválido"

def test_http_exception(client):
    resp = client.get("/ruta-no-existe")
    data = resp.get_json()
    assert resp.status_code == 404
    assert data["code"] == "Not Found"
    assert "message" in data

def test_generic_exception(client):
    resp = client.get("/generic-error")
    data = resp.get_json()
    assert resp.status_code == 500
    assert data["code"] == "InternalServerError"
    assert data["message"] == "Ha ocurrido un error inesperado 🚨"