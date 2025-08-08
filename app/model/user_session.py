from datetime import datetime, timezone
from typing import Optional
from bson import SON, ObjectId


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
        self.user_id = user_id
        self.device_id = device_id
        self.ip_address = ip_address
        self.browser = browser
        self.os = os
        self.login_at = login_at
        self.refresh_token = refresh_token
        self.is_revoked = is_revoked
        self.last_refresh_at = last_refresh_at
        self.revoked_at = revoked_at
        self.reason = reason
        self.status = status
        self.role = role

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "browser": self.browser,
            "os": self.os,
            "login_at": self.login_at,
            "refresh_token": self.refresh_token,
            "is_revoked": self.is_revoked,
            "last_refresh_at": self.last_refresh_at,
            "revoked_at": self.revoked_at,
            "reason": self.reason,
            "status": self.status,
            "role": self.role,
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
