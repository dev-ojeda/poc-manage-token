# conftest.py
from functools import wraps
import pytest
from flask import Flask
from unittest.mock import patch
from bson import ObjectId

from app.auth import AuthException
from app.backend.routes import backend_bp

# ===========================
#      APP & CLIENT
# ===========================

@pytest.fixture
def app():
    """Crea la app Flask para tests."""
    app = Flask(__name__)
    app.register_blueprint(backend_bp)
    app.testing = True

@pytest.fixture
def client(app):
    """Cliente de prueba para hacer requests."""
    return app.test_client()

# ===========================
#      HEADERS JWT
# ===========================

@pytest.fixture
def auth_headers():
    """Headers con token fake para endpoints protegidos."""
    return {"Authorization": "Bearer faketoken"}

# ===========================
#      MOCK SERVICES
# ===========================

@pytest.fixture(autouse=True)
def mock_services():
    """
    Mockea TODOS los servicios usados en backend.py con valores por defecto.
    Así los tests no dependen de la DB ni lógica real.
    """
    with patch("app.auth.services.user_service.UserService.get_user_by_username", return_value=None), \
         patch("app.auth.services.auth_service.AuthService.generate_tokens", return_value="fake-access"), \
         patch("app.auth.services.auth_service.AuthService.refresh_access_token", return_value="fake-refresh"), \
         patch("app.auth.services.auth_service.AuthService.get_refresh_token", return_value={"refresh_token": "fake-refresh"}), \
         patch("app.auth.services.auth_service.AuthService.revoke_old_token", return_value={"success": True}), \
         patch("app.auth.services.session_service.SessionService.register_session", return_value={"success": True}), \
         patch("app.auth.services.session_service.SessionService.update_session", return_value={"success": True}), \
         patch("app.auth.services.session_service.SessionService.get_active_session_by_Id", return_value=None), \
         patch("app.auth.services.blacklist_service.TokenBlacklistService.revoke_token_blacklist", return_value={"success": True}), \
         patch("app.auth.services.audit_service.AuditService.get_logs_audit", return_value={"success": True}), \
         patch("app.auth.services.audit_service.AuditService.update_session_activity", return_value=None), \
         patch("app.midleware.jwt_guard", mock_jwt_required):

         yield

# ===========================
#      MOCK JWT REQUIRED
# ===========================

@pytest.fixture
def mock_jwt_required():
    """Mock de jwt_required_custom que siempre inyecta un user fake"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            fake_payload = {"username": "neo", "role": "Admin"}
            return fn(fake_payload, *args, **kwargs)
        return wrapper
    return decorator

# ===========================
#      FIXTURE UTILES
# ===========================

@pytest.fixture
def fake_user_dict():
    """Diccionario de usuario fake."""
    return {"user_id": str(ObjectId()), "device_id": "dev123"}
