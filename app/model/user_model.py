import datetime
from datetime import timezone
from typing import Optional, Literal
from bson import ObjectId
import bcrypt


class UserModel:
    def __init__(
        self,
        username: str,
        password: str,
        rol: Literal["User", "Admin"],
        email: Optional[str] = None,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        failed_attempts: int = 0,
        blocked_until: Optional[datetime.datetime] = None,
        _id: Optional[ObjectId] = None,
        password_hashed: bool = False  # si True, no aplica hash de nuevo
    ):
        self._id = _id or ObjectId()
        self._username = username
        self._rol = rol
        self._email = email
        self._created_at = created_at or datetime.datetime.now(tz=timezone.utc)
        self._updated_at = updated_at or datetime.datetime.now(tz=timezone.utc)
        self._failed_attempts = failed_attempts
        self._blocked_until = blocked_until

        if password_hashed:
            self._password = password
        else:
            self.password = password  # aplica hash automáticamente vía setter

    # ------------------------------
    # Propiedades
    # ------------------------------
    @property
    def id(self) -> ObjectId:
        return self._id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        if not value:
            raise ValueError("Username no puede estar vacío")
        self._username = value

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, value: str):
        self._password = self.hash_password(value)

    @property
    def email(self) -> Optional[str]:
        return self._email

    @email.setter
    def email(self, value: Optional[str]):
        self._email = value

    @property
    def rol(self) -> Literal["User", "Admin"]:
        return self._rol

    @rol.setter
    def rol(self, value: Literal["User", "Admin"]):
        if value not in ["User", "Admin"]:
            raise ValueError("Rol debe ser 'User' o 'Admin'")
        self._rol = value

    @property
    def created_at(self) -> datetime.datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime.datetime:
        return self._updated_at

    @updated_at.setter
    def updated_at(self, value: datetime.datetime):
        self._updated_at = value

    @property
    def failed_attempts(self) -> int:
        return self._failed_attempts

    @failed_attempts.setter
    def failed_attempts(self, value: int):
        if value < 0:
            raise ValueError("failed_attempts no puede ser negativo")
        self._failed_attempts = value

    @property
    def blocked_until(self) -> Optional[datetime.datetime]:
        return self._blocked_until

    @blocked_until.setter
    def blocked_until(self, value: Optional[datetime.datetime]):
        self._blocked_until = value

    # ------------------------------
    # Métodos auxiliares
    # ------------------------------
    def to_dict(self) -> dict:
        return {
            "_id": self.id,
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "rol": self.rol,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "failed_attempts": self.failed_attempts,
            "blocked_until": self.blocked_until
        }

    def to_json(self) -> dict:
        d = self.to_dict()
        d["_id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat()
        d["updated_at"] = d["updated_at"].isoformat()
        if d["blocked_until"]:
            d["blocked_until"] = d["blocked_until"].isoformat()
        return d

    def is_blocked_now(self) -> bool:
        """Verifica si el usuario está bloqueado actualmente"""
        now = datetime.datetime.now(tz=timezone.utc)
        return self.blocked_until is not None and now < self.blocked_until.replace(tzinfo=timezone.utc)

    def update_timestamp(self) -> datetime.datetime:
        self.updated_at = datetime.datetime.now(tz=timezone.utc)
        return self.updated_at

    # ------------------------------
    # Métodos de clase
    # ------------------------------
    @staticmethod
    def from_dict(data: dict, password_hashed: bool = True) -> "UserModel":
        return UserModel(
            username=data.get("username"),
            password=data.get("password"),
            email=data.get("email"),
            rol=data.get("rol"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            failed_attempts=data.get("failed_attempts", 0),
            blocked_until=data.get("blocked_until"),
            _id=data.get("_id"),
            password_hashed=password_hashed
        )

    @staticmethod
    def hash_password(plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
