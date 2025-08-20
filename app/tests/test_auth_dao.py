from datetime import datetime, timedelta, timezone
import mongomock
import pytest
from app.dao.auth_dao import AuthDao

@pytest.fixture
def mock_db():
    client = mongomock.MongoClient(tz_aware=True, tzinfo=timezone.utc)
    return client["mdbManageToken"]

@pytest.fixture
def auth_dao(mock_db):
    dao = AuthDao()
    dao.db = mock_db
    dao.collection = mock_db["refresh_tokens"]
    return dao

@pytest.fixture
def sample_tokens():
    now = datetime.now(timezone.utc)
    return [
        {
            "username": "neo",
            "device_id": "device123",
            "jti": "jti_1",
            "refresh_token": "rtok123",
            "revoked_at": None,
            "expires_at": now + timedelta(hours=1),
            "created_at": now - timedelta(minutes=10),
            "used_at": now
        },
        {
            "username": "neo",
            "device_id": "device456",
            "jti": "jti_2",
            "refresh_token": "rtok456",
            "revoked_at": None,
            "expires_at": now - timedelta(hours=1),  # Expirado
            "created_at": now - timedelta(hours=2)
        },
        {
            "username": "trinity",
            "device_id": "device789",
            "jti": "jti_3",
            "refresh_token": "rtok789",
            "revoked_at": None,
            "expires_at": now + timedelta(hours=2),
            "created_at": now - timedelta(minutes=5)
        }
    ]

def test_get_active_token_by_user(auth_dao, sample_tokens):
    auth_dao.collection.insert_many(sample_tokens)
    now = datetime.now(timezone.utc)
    token = auth_dao.get_active_token_by_username("neo")
    assert token is not None
    assert not token["revoked_at"]
    assert token["expires_at"].replace(tzinfo=timezone.utc) > now

   
@pytest.mark.parametrize(
    "jti, expected_modified",
    [
        ("jti_1", 1),
        ("jti_999", 0)  # inexistente
    ]
)
def test_revoke_token_by_jti(auth_dao, sample_tokens, jti, expected_modified):
    auth_dao.collection.insert_many(sample_tokens)
    modified_count = auth_dao.revoke_token_by_jti(jti)
    assert modified_count == expected_modified
    if expected_modified:
        token = auth_dao.collection.find_one({"jti": jti})
        assert token["revoked_at"]

@pytest.mark.parametrize(
    "device_id, expected_modified",
    [
        ("device123", 1),
        ("device999", 0)
    ]
)
def test_revoke_token_by_device_id(auth_dao, sample_tokens, device_id, expected_modified):
    auth_dao.collection.insert_many(sample_tokens)
    modified_count = auth_dao.revoke_token_by_device_id(device_id)
    assert modified_count == expected_modified
    if expected_modified:
        token = auth_dao.collection.find_one({"device_id": device_id})
        assert token["revoked_at"]

@pytest.mark.parametrize(
    "username, expected_modified",
    [
        ("neo", 2),
        ("unknown", 0)
    ]
)
def test_revoke_all_tokens_for_user(auth_dao, sample_tokens, username, expected_modified):
    auth_dao.collection.insert_many(sample_tokens)
    modified_count = auth_dao.revoke_all_tokens_for_user(username)
    assert modified_count == expected_modified
    if expected_modified:
        tokens = list(auth_dao.collection.find({"username": username}))
        assert all(t["revoked_at"] for t in tokens)

def test_revoke_all_tokens_for_user_no_match(auth_dao, sample_tokens):
    """Debe devolver 0 si no encuentra tokens para revocar."""
    auth_dao.db["refresh_tokens"].insert_many(sample_tokens)

    modified_count = auth_dao.revoke_all_tokens_for_user("unknown_user")
    assert modified_count == 0

def test_revoke_token_by_jti_already_revoked(auth_dao, sample_tokens):
    """Si el token ya estaba revocado, no debe modificar nada."""
    sample_tokens[0]["revoked_at"] = True
    auth_dao.db["refresh_tokens"].insert_many(sample_tokens)

    modified_count = auth_dao.revoke_token_by_jti("jti_1")
    assert modified_count == 0

def test_get_active_token_by_user_no_tokens(auth_dao):
    """Debe devolver None si no hay tokens activos."""
    token = auth_dao.get_active_token_by_user_and_device("neo","device123")
    assert token is None

def test_get_active_token_by_user_and_device(auth_dao, sample_tokens):
    auth_dao.db["refresh_tokens"].insert_many(sample_tokens)
    now = datetime.now(timezone.utc)  # timezone-aware
    # Caso válido: existe token activo para ese device
    token = auth_dao.get_active_token_by_user_and_device("neo","device123")
    assert token is not None
    assert token["device_id"] == "device123"
    assert token["revoked_at"] is None
    assert float(token["expires_at"].timestamp()) > float(datetime.timestamp(now))

    # Caso inválido: token expirado en ese device
    auth_dao.db["refresh_tokens"].update_one({"device_id": "device123"}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}})
    token_none_expired = auth_dao.get_active_token_by_user_and_device("neo","device123")
    assert token_none_expired is None

def test_mark_token_as_used_existing(auth_dao, sample_tokens):
    """Debe marcar un token existente con used_at y ser timezone-aware UTC."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    document = {
        "username": "neo",
        "device_id": "device123",
        "jti": "jti_1",
        "refresh_token": "rtok123",
        "revoked_at": None,
        "expires_at": now + timedelta(hours=1),
        "created_at": now - timedelta(minutes=10),
        "refresh_attempts": 0,
        "browser": "Chromw",
        "os": "Windows",
        "ip_address": "127.0.0.1"
    }

    # Insertar token en la DB simulada
    auth_dao.db["refresh_tokens"].insert_one(document)

    # Ejecutar función que marca como usado
    modified_count = auth_dao.mark_token_as_used(
        username="neo",
        device_id="device123",
        jti="jti_1",
        refresh_token="rtok123",
        created_at=document["created_at"],
        expires_at=document["expires_at"],
        browser=document["browser"],
        os=document["os"],
        ip_address="127.0.0.1",
        refresh_attempts=0,
        upsert=False
    )

    assert modified_count == 1

    updated = auth_dao.collection.find_one({"jti": "jti_1"})
    assert "used_at" in updated
    assert isinstance(updated["used_at"], datetime)
    assert updated["used_at"].tzinfo is not None
    assert updated["used_at"].utcoffset() == timedelta(0)  # UTC
    assert updated["used_at"] > now - timedelta(seconds=1)  # no más viejo que "now"
