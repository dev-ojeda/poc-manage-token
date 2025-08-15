# models/user_session.py

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from bson import ObjectId


class UserSession:
    # Constantes / enums
    REASONS = {
        "ip_change",
        "user_agent_change",
        "revoked",
        "multiple_attempts",
        "logout",
        "expiration",
        "login",
    }

    STATUSES = {"active", "revoked", "expired"}

    def __init__(
        self,
        user_id: ObjectId | str,
        device_id: str,
        ip_address: str,
        browser: Optional[str],
        os: Optional[str],
        login_at: Optional[datetime] = None,
        refresh_token: Optional[str] = None,
        is_revoked: bool = False,
        last_refresh_at: Optional[datetime] = None,
        revoked_at: Optional[datetime] = None,
        reason: Optional[str] = None,
        status: str = "active",
        role: Optional[str] = None,
        session_id: Optional[ObjectId | str] = None,
    ):
        # Identificadores
        self._user_id = self._ensure_objectid(user_id)
        self._session_id = self._ensure_objectid(session_id) if session_id is not None else None

        # Campos obligatorios
        self.device_id = device_id
        self.ip_address = ip_address
        self.browser = browser
        self.os = os

        now = datetime.now(timezone.utc)
        self.login_at = login_at or now
        self.last_refresh_at = last_refresh_at
        self.refresh_token = refresh_token

        # Estado
        self.is_revoked = bool(is_revoked)
        self.revoked_at = revoked_at
        self.reason = reason
        self.status = status
        self.role = role

    # -------------------
    # Helper static
    # -------------------
    @staticmethod
    def _ensure_objectid(value: Any) -> ObjectId:
        if isinstance(value, ObjectId):
            return value
        if value is None:
            raise ValueError("ObjectId requerido, se recibió None")
        try:
            return ObjectId(str(value))
        except Exception as e:
            raise ValueError(f"Valor inválido para ObjectId: {value}") from e

    # -------------------
    # Propiedades (getters / setters)
    # -------------------
    @property
    def session_id(self) -> Optional[ObjectId]:
        return self._session_id

    @session_id.setter
    def session_id(self, v: ObjectId | str | None):
        self._session_id = self._ensure_objectid(v) if v is not None else None

    @property
    def user_id(self) -> ObjectId:
        return self._user_id

    @user_id.setter
    def user_id(self, v: ObjectId | str):
        self._user_id = self._ensure_objectid(v)

    @property
    def device_id(self) -> str:
        return self._device_id

    @device_id.setter
    def device_id(self, v: str):
        if not v or not isinstance(v, str):
            raise ValueError("device_id debe ser un string no vacío")
        self._device_id = v

    @property
    def ip_address(self) -> str:
        return self._ip_address

    @ip_address.setter
    def ip_address(self, v: str):
        if not v or not isinstance(v, str):
            raise ValueError("ip_address debe ser un string no vacío")
        self._ip_address = v

    @property
    def browser(self) -> Optional[str]:
        return self._browser

    @browser.setter
    def browser(self, v: Optional[str]):
        self._browser = None if v is None else str(v)

    @property
    def os(self) -> Optional[str]:
        return self._os

    @os.setter
    def os(self, v: Optional[str]):
        self._os = None if v is None else str(v)

    @property
    def login_at(self) -> datetime:
        return self._login_at

    @login_at.setter
    def login_at(self, v: datetime):
        if not isinstance(v, datetime):
            raise ValueError("login_at debe ser datetime")
        self._login_at = v.astimezone(timezone.utc)

    @property
    def last_refresh_at(self) -> Optional[datetime]:
        return self._last_refresh_at

    @last_refresh_at.setter
    def last_refresh_at(self, v: Optional[datetime]):
        if v is not None and not isinstance(v, datetime):
            raise ValueError("last_refresh_at debe ser datetime o None")
        self._last_refresh_at = v.astimezone(timezone.utc) if v is not None else None

    @property
    def refresh_token(self) -> Optional[str]:
        return self._refresh_token

    @refresh_token.setter
    def refresh_token(self, v: Optional[str]):
        self._refresh_token = None if v is None else str(v)

    @property
    def is_revoked(self) -> bool:
        return self._is_revoked

    @is_revoked.setter
    def is_revoked(self, v: bool):
        self._is_revoked = bool(v)

    @property
    def revoked_at(self) -> Optional[datetime]:
        return self._revoked_at

    @revoked_at.setter
    def revoked_at(self, v: Optional[datetime]):
        if v is not None and not isinstance(v, datetime):
            raise ValueError("revoked_at debe ser datetime o None")
        self._revoked_at = v.astimezone(timezone.utc) if v is not None else None

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    @reason.setter
    def reason(self, v: Optional[str]):
        if v is not None:
            v = str(v)
            if v not in self.REASONS:
                raise ValueError(f"reason inválido. Debe ser uno de {sorted(self.REASONS)}")
        self._reason = v

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, v: str):
        if v not in self.STATUSES:
            raise ValueError(f"status inválido. Debe ser uno de {sorted(self.STATUSES)}")
        self._status = v

    @property
    def role(self) -> Optional[str]:
        return self._role

    @role.setter
    def role(self, v: Optional[str]):
        self._role = None if v is None else str(v)

    # -------------------
    # Operaciones comunes
    # -------------------
    def to_dict(self, for_insert: bool = True) -> Dict:
        """
        Serializa para MongoDB.
        if for_insert: no incluye _id si es None; si session_id existe lo convierte.
        """
        doc = {
            "user_id": self.user_id,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "browser": self.browser,
            "os": self.os,
            "login_at": self.login_at,
            "last_refresh_at": self.last_refresh_at,
            "refresh_token": self.refresh_token,
            "is_revoked": self.is_revoked,
            "revoked_at": self.revoked_at,
            "reason": self.reason,
            "status": self.status,
            "role": self.role,
        }
        if self.session_id is not None:
            doc["_id"] = self.session_id
        # Si for_insert y _id es None, lo omitimos (Mongo autogenera)
        return doc

    @classmethod
    def from_dict(cls, data: Dict) -> "UserSession":
        """
        Construye un UserSession desde un documento Mongo (o dict equivalente).
        Acepta user_id / _id en formatos str o ObjectId.
        """
        session_id = data.get("_id") or data.get("session_id")
        user_id = data.get("user_id") or data.get("usuario_id")
        return cls(
            user_id=user_id,
            device_id=data.get("device_id"),
            ip_address=data.get("ip_address"),
            browser=data.get("browser"),
            os=data.get("os"),
            login_at=data.get("login_at"),
            refresh_token=data.get("refresh_token"),
            is_revoked=data.get("is_revoked", False),
            last_refresh_at=data.get("last_refresh_at"),
            revoked_at=data.get("revoked_at"),
            reason=data.get("reason"),
            status=data.get("status", "active"),
            role=data.get("role"),
            session_id=session_id,
        )

    # -------------------
    # Acciones útiles
    # -------------------
    def revoke(self, reason: str = "revoked") -> None:
        """Marca sesión como revocada y fechas asociadas."""
        if reason not in self.REASONS:
            raise ValueError("reason inválido al revocar")
        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)
        self.reason = reason
        self.status = "revoked"

    def mark_expired(self) -> None:
        self.status = "expired"
        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)
        self.reason = "expiration"

    def touch_last_refresh(self, at: Optional[datetime] = None) -> None:
        self.last_refresh_at = (at or datetime.now(timezone.utc))

    def is_active(self) -> bool:
        return (not self.is_revoked) and (self.status == "active")

    # Comparadores convenientes
    def same_device(self, device_id: str) -> bool:
        return self.device_id == device_id

    def __repr__(self) -> str:
        sid = str(self.session_id) if self.session_id else "<new>"
        return f"<UserSession {sid} user={str(self.user_id)} device={self.device_id} status={self.status}>"
