from datetime import datetime
from typing import Optional
from bson import ObjectId

class UserSession:
    def __init__(
        self,
        user_id: ObjectId,
        device_id: str,
        ip_address: str,
        browser: str,
        os: str,
        login_at: datetime,
        refresh_token: str,
        is_revoked: bool = False,
        last_refresh_at: Optional[datetime] = None,
        revoked_at: Optional[datetime] = None,
        reason: Optional[str] = None,
        status: str = "active",
        role: Optional[str] = None
    ):
        self._user_id = user_id
        self._device_id = device_id
        self._ip_address = ip_address
        self._browser = browser
        self._os = os
        self._login_at = login_at
        self._refresh_token = refresh_token
        self._is_revoked = is_revoked
        self._last_refresh_at = last_refresh_at
        self._revoked_at = revoked_at
        self._reason = reason
        self._status = status
        self._role = role

    # user_id (solo getter, no cambia)
    @property
    def user_id(self) -> ObjectId:
        return self._user_id

    # device_id
    @property
    def device_id(self) -> str:
        return self._device_id

    @device_id.setter
    def device_id(self, value: str):
        if not value:
            raise ValueError("device_id no puede estar vacío")
        self._device_id = value

    # ip_address
    @property
    def ip_address(self) -> str:
        return self._ip_address

    @ip_address.setter
    def ip_address(self, value: str):
        # Aquí podrías validar formato IP si quieres
        self._ip_address = value

    # browser
    @property
    def browser(self) -> str:
        return self._browser

    @browser.setter
    def browser(self, value: str):
        self._browser = value

    # os
    @property
    def os(self) -> str:
        return self._os

    @os.setter
    def os(self, value: str):
        self._os = value

    # login_at (solo getter)
    @property
    def login_at(self) -> datetime:
        return self._login_at

    # refresh_token
    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    @refresh_token.setter
    def refresh_token(self, value: str):
        if not value:
            raise ValueError("refresh_token no puede estar vacío")
        self._refresh_token = value

    # is_revoked
    @property
    def is_revoked(self) -> bool:
        return self._is_revoked

    @is_revoked.setter
    def is_revoked(self, value: bool):
        self._is_revoked = bool(value)

    # last_refresh_at
    @property
    def last_refresh_at(self) -> Optional[datetime]:
        return self._last_refresh_at

    @last_refresh_at.setter
    def last_refresh_at(self, value: Optional[datetime]):
        self._last_refresh_at = value

    # revoked_at
    @property
    def revoked_at(self) -> Optional[datetime]:
        return self._revoked_at

    @revoked_at.setter
    def revoked_at(self, value: Optional[datetime]):
        self._revoked_at = value

    # reason
    @property
    def reason(self) -> Optional[str]:
        return self._reason

    @reason.setter
    def reason(self, value: Optional[str]):
        self._reason = value

    # status
    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str):
        allowed = ["active", "inactive", "revoked"]
        if value not in allowed:
            raise ValueError(f"status debe ser uno de {allowed}")
        self._status = value

    # role
    @property
    def role(self) -> Optional[str]:
        return self._role

    @role.setter
    def role(self, value: Optional[str]):
        self._role = value

    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "device_id": self._device_id,
            "ip_address": self._ip_address,
            "browser": self._browser,
            "os": self._os,
            "login_at": self._login_at,
            "refresh_token": self._refresh_token,
            "is_revoked": self._is_revoked,
            "last_refresh_at": self._last_refresh_at,
            "revoked_at": self._revoked_at,
            "reason": self._reason,
            "status": self._status,
            "role": self._role,
        }

    @staticmethod
    def from_dict(data: dict) -> "UserSession":
        return UserSession(
            user_id=data["user_id"],
            device_id=data["device_id"],
            ip_address=data["ip_address"],
            browser=data["browser"],
            os=data["os"],
            login_at=data["login_at"],
            refresh_token=data["refresh_token"],
            is_revoked=data.get("is_revoked", False),
            last_refresh_at=data.get("last_refresh_at"),
            revoked_at=data.get("revoked_at"),
            reason=data.get("reason"),
            status=data.get("status", "active"),
            role=data.get("role")
        )
