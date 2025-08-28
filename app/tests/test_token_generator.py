import pytest
import jwt
from app.model import TokenGeneratorModel
from app.auth import AuthException
from uuid import uuid4
@pytest.fixture
def token_gen():
    return TokenGeneratorModel()

@pytest.fixture
def user_data():
    jti = str(uuid4())
    device_id = str(uuid4())
    return {
        "username": "user@example.com",
        "rol": "User",
        "device_id": device_id,
        "jti": jti
    }

@pytest.fixture
def admin_data():
    return {
        "username": "adminuser",
        "rol": "Admin",
        "scope": "full_control",
        "jti": "admin-jti"
    }

def test_create_tokens_user(token_gen, user_data):
    access, refresh = token_gen.create_tokens(user_data)
    decoded_access = jwt.decode(access, token_gen.public_key, algorithms=["RS256"], audience=None, options={"verify_aud": False})
    decoded_refresh = jwt.decode(refresh, token_gen.public_key, algorithms=["RS256"], audience=None, options={"verify_aud": False})
    assert decoded_access["sub"] == user_data["username"]
    assert decoded_refresh["sub"] == user_data["username"]
    assert decoded_access["rol"] == "User"

def test_create_tokens_admin(token_gen, admin_data):
    access, refresh = token_gen.create_tokens(admin_data)
    decoded_access = jwt.decode(access, token_gen.public_key, algorithms=["RS256"], audience=None, options={"verify_aud": False})
    assert decoded_access["rol"] == "Admin"

def test_refresh_access_token(token_gen, user_data):
    _, refresh = token_gen.create_tokens(user_data)
    new_access = token_gen.refresh_access_token(refresh)
    decoded = jwt.decode(new_access, token_gen.public_key, algorithms=["RS256"], audience=None, options={"verify_aud": False})
    assert decoded["sub"] == user_data["username"]
    assert decoded["rol"] == "User"

def test_create_tokens_global(token_gen):
    token = token_gen.create_tokens_global()
    decoded = token_gen.verify_token_global(token)
    assert decoded["rol"] == "Admin"
    assert decoded["scope"] == "full_control"

def test_verify_token_invalid_type(token_gen, user_data):
    access, refresh = token_gen.create_tokens(user_data)
    with pytest.raises(AuthException):
       token_gen.verify_token(refresh, expected_type="access")

def test_get_role_from_token(token_gen, user_data):
    access, _ = token_gen.create_tokens(user_data)
    role = token_gen.get_role_from_token(access)
    assert role == "User"

def test_decode_expired_token(token_gen, user_data):
    # Creamos un token expirado
    expired_payload = token_gen._build_payload(user_data, "access", -10)
    expired_token = jwt.encode(expired_payload, token_gen.private_key, algorithm="RS256")
    validar_epired = token_gen.verify_token(expired_token)
    assert "ExpiredSignatureError" in validar_epired["code"] or "401" in str(validar_epired["status"])

def test_decode_invalid_signature(token_gen, user_data):
    access, _ = token_gen.create_tokens(user_data)
    tampered = access + "tamper"
    with pytest.raises(AuthException):
        token_gen.verify_token(tampered)
