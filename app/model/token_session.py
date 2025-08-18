from datetime import datetime, timezone
from bson import ObjectId

class TokenSession:
    def __init__(
        self,
        username: str,
        device_id: str,
        jti: str,
        refresh_token: str,
        created_at: datetime,
        expires_at: datetime,
        update_at: datetime = None,
        revoked_at: datetime = None,
        used_at: datetime = None,
        refresh_attempts: int = 0,
        browser: str = None,
        os: str = None,
        user_agent: str = None,
        ip_address: str = None,
        _id: ObjectId = None
    ):
        self._id = _id or ObjectId()
        self.username = username
        self.device_id = device_id
        self.jti = jti
        self.refresh_token = refresh_token
        self.created_at = created_at
        self.update_at = update_at
        self.expires_at = expires_at
        self.revoked_at = revoked_at
        self.used_at = used_at
        self.refresh_attempts = refresh_attempts
        self.browser = browser
        self.os = os
        self.user_agent = user_agent
        self.ip_address = ip_address

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "username": self.username,
            "device_id": self.device_id,
            "jti": self.jti,
            "refresh_token": self.refresh_token,
            "created_at": self.created_at,
            "update_at": self.update_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "used_at": self.used_at,
            "refresh_attempts": self.refresh_attempts,
            "browser": self.browser,
            "os": self.os,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            _id=data.get("_id"),
            username=data["username"],
            device_id=data["device_id"],
            jti=data["jti"],
            refresh_token=data["refresh_token"],
            created_at=data["created_at"],
            update_at=data.get("update_at"),
            expires_at=data["expires_at"],
            revoked_at=data.get("revoked_at"),
            used_at=data.get("used_at"),
            refresh_attempts=data.get("refresh_attempts", 0),
            browser=data.get("browser"),
            os=data.get("os"),
            user_agent=data.get("user_agent"),
            ip_address=data.get("ip_address")
        )

    def revoke(self):
        """Revoca la sesión marcando revoked_at"""
        self.revoked_at = datetime.now(timezone.utc)

    def increment_attempts(self):
        """Incrementa los intentos de refresco"""
        if self.refresh_attempts < 3:
            self.refresh_attempts += 1
        else:
            raise ValueError("Máximo de intentos de refresco alcanzado")

    def is_expired(self) -> bool:
        """Verifica si el token expiró"""
        return datetime.now(timezone.utc) > self.expires_at

    def mark_used(self):
        """Marca el token como usado"""
        self.used_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Verifica si el token está activo (no expirado, no revocado)"""
        return not self.is_expired() and self.revoked_at is None    