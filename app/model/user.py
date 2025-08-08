#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timezone
from typing import Optional, Literal
from bson import ObjectId
import bcrypt

class User:
    def __init__(
        self,
        username: str,
        password: str,
        rol: Literal["User", "Admin"],
        email: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        failed_attempts: int = 0,
        blocked_until: Optional[datetime] = None,
        _id: Optional[ObjectId] = None,
        already_hashed: bool = False
    ):
        self._id = _id or ObjectId()
        self.username = username
        self.password = password if already_hashed else self.hash_password(password)
        self.email = email
        self.rol = rol
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.failed_attempts = failed_attempts
        self.blocked_until = blocked_until

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "rol": self.rol,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "failed_attempts": self.failed_attempts,
            "blocked_until": self.blocked_until
        }

    def to_json(self):
        d = self.to_dict()
        d["_id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat()
        d["updated_at"] = d["updated_at"].isoformat()
        if d["blocked_until"]:
            d["blocked_until"] = d["blocked_until"].isoformat()
        return d

    def is_blocked_now(self) -> bool:
        return self.blocked_until is not None and self.update_timestamp() < self.blocked_until.replace(tzinfo=timezone.utc)

    def update_timestamp(self) -> datetime:
        self.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def from_dict(data: dict) -> "User":
        return User(
            username=data.get("username"),
            password=data.get("password"),
            email=data.get("email"),
            rol=data.get("rol"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            failed_attempts=data.get("failed_attempts", 0),
            blocked_until=data.get("blocked_until"),
            _id=data.get("_id"),
            already_hashed=True  # 🔐 evitar doble hash al cargar desde Mongo
        )

    @staticmethod
    def hash_password(plain_password):
        return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
