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
        self._username = username
        # Usamos el setter para que aplique hash si es necesario
        self.password = password if already_hashed else self.hash_password(password)
        self._email = email
        self._rol = rol
        self._created_at = created_at or datetime.now(timezone.utc)
        self._updated_at = updated_at or datetime.now(timezone.utc)
        self._failed_attempts = failed_attempts
        self._blocked_until = blocked_until

    # Getter y setter para _id (solo getter porque el id no debería cambiar)
    @property
    def id(self) -> ObjectId:
        return self._id

    # Getter y setter para username
    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        # Aquí podrías validar, ej. que no esté vacío
        if not value:
            raise ValueError("Username no puede estar vacío")
        self._username = value

    # Getter y setter para password (settear con hash)
    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, plain_password: str):
        # Siempre guarda la versión hasheada
        self._password = self.hash_password(plain_password)

    # Getter y setter para email
    @property
    def email(self) -> Optional[str]:
        return self._email

    @email.setter
    def email(self, value: Optional[str]):
        # Aquí podrías validar formato email si quieres
        self._email = value

    # Getter y setter para rol
    @property
    def rol(self) -> Literal["User", "Admin"]:
        return self._rol

    @rol.setter
    def rol(self, value: Literal["User", "Admin"]):
        if value not in ["User", "Admin"]:
            raise ValueError("Rol debe ser 'User' o 'Admin'")
        self._rol = value

    # created_at solo getter (no se debe cambiar)
    @property
    def created_at(self) -> datetime:
        return self._created_at

    # updated_at getter y setter
    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @updated_at.setter
    def updated_at(self, value: datetime):
        self._updated_at = value

    # failed_attempts getter y setter
    @property
    def failed_attempts(self) -> int:
        return self._failed_attempts

    @failed_attempts.setter
    def failed_attempts(self, value: int):
        if value < 0:
            raise ValueError("failed_attempts no puede ser negativo")
        self._failed_attempts = value

    # blocked_until getter y setter
    @property
    def blocked_until(self) -> Optional[datetime]:
        return self._blocked_until

    @blocked_until.setter
    def blocked_until(self, value: Optional[datetime]):
        self._blocked_until = value

    # Métodos que ya tenías (sin cambios salvo usar propiedades internas)
    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "username": self._username,
            "password": self._password,
            "email": self._email,
            "rol": self._rol,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "failed_attempts": self._failed_attempts,
            "blocked_until": self._blocked_until
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
        return self.updated_at

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
