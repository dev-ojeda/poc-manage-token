# tests/test_session_dao.py
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import pytest
from unittest.mock import MagicMock

from app.dao.session_dao import SessionDAO
from app.model.user_session import UserSession

@pytest.fixture
def mock_dao():
    dao = SessionDAO()
    dao.db = MagicMock()

    # Mockeamos find_one
    dao.db.find_one.return_value = {
        "_id": ObjectId(),
        "device_id": "device123",
        "user_id": ObjectId(),
        "is_revoked": False,
        "status": "active",
        "reason": "login",
        "login_at": datetime.now(timezone.utc),
        "last_refresh_at": datetime.now(timezone.utc)
    }

    # Mockeamos update_with_log
    dao.db.update_with_log.return_value = {"modified_count": 1}
     # Mockeamos insert_with_log
    dao.db.insert_with_log.return_value = {"inserted_id": ObjectId()}

    # Mock count_documents
    dao.db.count_documents.return_value = 1

    # Mock aggregate
    dao.db.aggregate.return_value = [{
        "_id": ObjectId(),
        "user_id": ObjectId(),
        "device_id": "device123",
        "ip_address": "127.0.0.1",
        "browser": "Chrome",
        "os": "Windows",
        "login_at": datetime.now(timezone.utc),
        "last_refresh_at": datetime.now(timezone.utc),
        "refresh_token": "token123",
        "is_revoked": False,
        "reason": "login",
        "status": "active",
        "user_data": {
            "username": "neo",
            "email": "neo@test.com",
            "rol": "User"
        }
    }]


    return dao

@pytest.fixture
def sample_session():
    now = datetime.now(timezone.utc)
    return UserSession(
        user_id=ObjectId(),
        device_id="device123",
        ip_address="127.0.0.1",
        browser="Chrome",
        os="Windows",
        login_at=now,
        last_refresh_at=now,
        refresh_token="token123",
        is_revoked=False,
        reason="login",
        status="active"
    )

def test_insert_session(mock_dao):
    session = UserSession(
        user_id=ObjectId(),
        device_id="device123",
        ip_address="127.0.0.1",
        browser="Chrome",
        os="Windows",
        login_at=datetime.now(timezone.utc),
        last_refresh_at=datetime.now(timezone.utc),
        refresh_token="token123",
        is_revoked=False,
        reason="login"
    )
    result = mock_dao.insert_session(session)
    assert "inserted_id" in result
    mock_dao.db.insert_with_log.assert_called_once()

def test_get_active_session(mock_dao):
    user_id = ObjectId()
    result = mock_dao.get_active_session(user_id, "device123")
    assert result["device_id"] == "device123"
    mock_dao.db.find_one.assert_called()

def test_device_id_exists(mock_dao):
    result = mock_dao.device_id_exists("device123")
    assert result["device_id"] == "device123"
    mock_dao.db.find_one.assert_called()

def test_revoked_session(mock_dao):
    user_id = ObjectId()
    result = mock_dao.revoked_session(user_id, reason="revoked")
    assert result["modified_count"] == 1
    mock_dao.db.update_with_log.assert_called()

def test_update_session(mock_dao):
    user_id = ObjectId()
    result = mock_dao.update_session(user_id, token="token123", reason="active")
    assert result["modified_count"] == 1
    mock_dao.db.update_with_log.assert_called()

def test_update_session_for_audit(mock_dao):
    user_id = ObjectId()
    result = mock_dao.update_session_for_audit(user_id, ip_address="127.0.0.1", browser="Chrome", reason="audit")
    assert result["modified_count"] == 1
    mock_dao.db.update_with_log.assert_called()

def test_has_active_session(mock_dao):
    user_id = ObjectId()
    result = mock_dao.has_active_session(user_id)
    assert result is True
    mock_dao.db.count_documents.assert_called()

def test_get_active_sessions_with_user_data(mock_dao):
    result = mock_dao.get_active_sessions_with_user_data()
    print(result[0]["user_data"]["username"])
    assert isinstance(result, list)
    assert result[0]["user_data"]["username"] == "neo"
    mock_dao.db.aggregate.assert_called()
