from datetime import datetime
from typing import Optional


class AuditLog:
    VALID_EVENT_TYPES = {"ip_change", "user_agent_change", "revoked", "login", "logout", "refresh_token"}

    def __init__(
        self,
        session_id: str,
        user_id: str,
        event_type: str,
        old_value: str,
        new_value: str,
        timestamp: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.event_type = event_type
        self.old_value = old_value
        self.new_value = new_value
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = timestamp

    # --- session_id ---
    @property
    def session_id(self) -> str:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("session_id debe ser un string no vacío")
        self._session_id = value

    # --- user_id ---
    @property
    def user_id(self) -> str:
        return self._user_id

    @user_id.setter
    def user_id(self, value: str):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("user_id debe ser un string no vacío")
        self._user_id = value

    # --- event_type ---
    @property
    def event_type(self) -> str:
        return self._event_type

    @event_type.setter
    def event_type(self, value: str):
        if value not in self.VALID_EVENT_TYPES:
            raise ValueError(f"event_type debe ser uno de {self.VALID_EVENT_TYPES}")
        self._event_type = value

    # --- old_value ---
    @property
    def old_value(self) -> str:
        return self._old_value

    @old_value.setter
    def old_value(self, value: str):
        if not isinstance(value, str):
            raise ValueError("old_value debe ser string")
        self._old_value = value

    # --- new_value ---
    @property
    def new_value(self) -> str:
        return self._new_value

    @new_value.setter
    def new_value(self, value: str):
        if not isinstance(value, str):
            raise ValueError("new_value debe ser string")
        self._new_value = value

    # --- ip_address ---
    @property
    def ip_address(self) -> Optional[str]:
        return self._ip_address

    @ip_address.setter
    def ip_address(self, value: Optional[str]):
        if value is not None and not isinstance(value, str):
            raise ValueError("ip_address debe ser string o None")
        self._ip_address = value

    # --- user_agent ---
    @property
    def user_agent(self) -> Optional[str]:
        return self._user_agent

    @user_agent.setter
    def user_agent(self, value: Optional[str]):
        if value is not None and not isinstance(value, str):
            raise ValueError("user_agent debe ser string o None")
        self._user_agent = value

    # --- timestamp ---
    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: datetime):
        if not isinstance(value, datetime):
            raise ValueError("timestamp debe ser un objeto datetime")
        self._timestamp = value

    # --- Serialización para MongoDB ---
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp
        }

    # --- Construir desde MongoDB ---
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            event_type=data.get("event_type"),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            timestamp=data.get("timestamp") if isinstance(data.get("timestamp"), datetime) else datetime.fromisoformat(data.get("timestamp"))
        )
