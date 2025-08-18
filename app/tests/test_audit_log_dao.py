import pytest
import mongomock
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from app.dao.audit_dao import AuditLogDAO
from app.model.audit_session import AuditLog


# --- Fixtures ---
@pytest.fixture
def mock_db(monkeypatch):
    client = mongomock.MongoClient()
    db = client["mdbManageToken"]

    # Parcheamos el MongoDatabase usado dentro del DAO
    class FakeMongoDB:
        def __init__(self):
            self.db = db

        def insert_with_log(self, collection, document, context=""):
            self.db[collection].insert_one(document)
            return document

        def aggregate(self, collection, pipeline):
            return self.db[collection].aggregate(pipeline)

    monkeypatch.setattr("app.dao.audit_dao.MongoDatabase", FakeMongoDB)
    return db


@pytest.fixture
def audit_dao(mock_db):
    return AuditLogDAO()


@pytest.fixture
def sample_logs():
    now = datetime.now(timezone.utc)
    return  [
        {
            "session_id": str(ObjectId()),
            "user_id": "user1",
            "event_type": "login",
            "old_value": "Firefox",
            "new_value": "Chrome",
            "ip_address": "127.0.0.1",
            "user_agent": "pytest-agent",
            "timestamp": now - timedelta(minutes=5)
        },
        {
            "session_id": str(ObjectId()),
            "user_id": "user1",
            "event_type": "login",
            "old_value": "active",
            "new_value": "ended",
            "ip_address": "127.0.0.1",
            "user_agent": "pytest-agent",
            "timestamp": now - timedelta(minutes=1)
        },
        {
            "session_id": str(ObjectId()),
            "user_id": "user2",
            "event_type": "login",
            "old_value": "fail",
            "new_value": "success",
            "ip_address": "10.0.0.1",
            "user_agent": "pytest-agent",
            "timestamp": now
        }
    ]


# --- Tests ---
def test_insert_logs_audit(audit_dao, mock_db):
    log = AuditLog(
        session_id=str(ObjectId()),
        user_id="userX",
        event_type="login",
        old_value="",
        new_value="success",
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
        timestamp=datetime.now(timezone.utc)
    )
    result = audit_dao.insert_logs_audit(log, context="test")
    assert result["user_id"] == "userX"

    # Verificar que efectivamente se guardó
    saved = mock_db["session_audit"].find_one({"user_id": "userX"})
    assert saved is not None


def test_get_logs_audit_all(audit_dao, mock_db, sample_logs):
    mock_db["session_audit"].insert_many(sample_logs)
    params = {
            "user_id": "user1",
            "event_type": "login",
            "start": None,
            "end": None,
            "page": 1,
            "limit": 10
        }
    result = audit_dao.get_logs_audit(**params)
    assert result["total_count"] == 2
    assert len(result["logs"]) == 2
    assert all("timestamp" in log for log in result["logs"])
    assert isinstance(result["logs"][0]["timestamp"], str)  # convertido a ISO


def test_get_logs_audit_filter_user(audit_dao, mock_db, sample_logs):
    mock_db["session_audit"].insert_many(sample_logs)

    result = audit_dao.get_logs_audit(user_id="user1")
    assert result["total_count"] == 2
    assert all(log["user_id"] == "user1" for log in result["logs"])


def test_get_logs_audit_filter_event_type(audit_dao, mock_db, sample_logs):
    mock_db["session_audit"].insert_many(sample_logs)

    result = audit_dao.get_logs_audit(event_type="login")
    assert result["total_count"] == 3
    assert all(log["event_type"] == "login" for log in result["logs"])


def test_get_logs_audit_with_pagination(audit_dao, mock_db, sample_logs):
    mock_db["session_audit"].insert_many(sample_logs)

    result = audit_dao.get_logs_audit(page=1, limit=2)
    assert len(result["logs"]) == 2
    assert result["page"] == 1
    assert result["limit"] == 2


def test_get_logs_audit_date_range(audit_dao, mock_db, sample_logs):
    mock_db["session_audit"].insert_many(sample_logs)
    now = datetime.now(timezone.utc).timestamp()

    # Solo debería traer los últimos 2 eventos
    result = audit_dao.get_logs_audit(start=now - 180, end=now)
    assert result["total_count"] == 2
