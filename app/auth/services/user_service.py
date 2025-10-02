import datetime
from datetime import timedelta, timezone
from typing import List, Optional

from bson import ObjectId

from app.auth.services.auth_service import AuthService
from app.model.user_model import UserModel
from app.dao.user_dao import UserDAO


class UserService:
    """
    Servicio de gestión de usuarios y autenticación.
    Maneja login, intentos fallidos, bloqueo y persistencia de tokens.
    """
    MAX_ATTEMPTS = 3
    BLOCK_TIME_SECONDS = 120  # 2 minutos

    def __init__(self):
        self.user_dao = UserDAO()
        self.auth_service = AuthService()

    # ==============================================================
    # LOGIN PRINCIPAL
    # ==============================================================
    def get_user_login(self, username: str, password: str, device_id: str, user_agent: dict, ip: str) -> dict:
        user = self.get_user_by_username(username)
        if not user:
            return {"success": False, "msg": "Usuario no encontrado", "code": "INVALID_USER", "status": 401}

        # 1. Verificar bloqueo
        blocked = self.is_user_blocked(username)
        if not blocked["success"]:
            return blocked

        # 2. Validar credenciales
        auth = self.validate_and_authenticate(username, password)
        if not auth["success"]:
            return auth
        user = auth["user"]

        # 3. Resetear intentos
        self.reset_login_attempts(user)
        # 4. Generar tokens
        # tokens = self.build_token_pair(payload=user.to_dict(), device_id=device_id)
        tokens = self.build_token_pair(payload=user.to_dict(), device_id=device_id)

        # 5. Persistir refresh token
        persisted = self.persist_user_token(user, tokens["refresh_token"], user_agent, ip)
        if not persisted.get("success", True):
            return {"success": False, "msg": "Error al persistir token", "code": "TOKEN_PERSIST_FAIL", "status": 500}

        return {"success": True, **tokens, "data": user.to_dict(), "status": 200}

    # ==============================================================
    # CONSULTAS DE USUARIO
    # ==============================================================
    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        return self.user_dao.find_by_username(username)

    def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        return self.user_dao.find_by_id(user_id)

    def get_ids_users(self) -> List[ObjectId]:
        return self.user_dao.find_ids_users()

    def get_all_users(self) -> dict:
        return self.user_dao.get_all_users()

    # ==============================================================
    # VALIDACIÓN DE PAYLOAD
    # ==============================================================
    def validate_login_payload(self, data: dict) -> List[str]:
        required_fields = ['username', 'password', 'device', 'rol', 'user_agent']
        return [field for field in required_fields if not data.get(field)]

    # ==============================================================
    # AUTENTICACIÓN
    # ==============================================================
    def authenticate_user(self, username: str, password: str) -> Optional[UserModel]:
        user = self.get_user_by_username(username)
        if user and UserModel.verify_password(password, user.password):
            return user
        return None

    # ==============================================================
    # INTENTOS FALLIDOS Y BLOQUEO
    # ==============================================================
    def handle_failed_login(self, username: str) -> dict:
        user: UserModel = self.get_user_by_username(username)
        if not user:
            return {"success": False, "msg": "Usuario no encontrado"}

        attempts = user.failed_attempts + 1
        update_fields = {"failed_attempts": attempts}

        if attempts >= self.MAX_ATTEMPTS:
            update_fields.update({
                "blocked_until": self._blocked_until(),
                "failed_attempts": 0
            })

        return self.user_dao.update(
            {"username": user.username, "rol": user.rol},
            {"$set": update_fields},
            upsert=True,
            context="Intentos Fallidos"
        )

    def reset_login_attempts(self, user: UserModel) -> dict:
        return self.user_dao.reset_login_attempts(user=user)

    def _blocked_until(self) -> datetime.datetime:
        return datetime.datetime.now(tz=timezone.utc) + timedelta(seconds=self.BLOCK_TIME_SECONDS)

    # ==============================================================
    # SOPORTE EXTRA PARA ENDPOINTS
    # ==============================================================
    def is_user_blocked(self, username: str) -> dict:
        user = self.get_user_by_username(username)
        if not user:
            return {"success": False, "msg": "Usuario no encontrado", "code": "INVALID_USER", "status": 404}

        if user.is_blocked_now():
            return {
                "success": False,
                "msg": "⏳ Usuario temporalmente bloqueado",
                "bloqueado_hasta": float(user.blocked_until.timestamp()),
                "code": "USER_BLOCKED",
                "status": 403
            }
        return {"success": True, "msg": "Usuario activo", "code": "USER_ACTIVE", "status": 200}

    def validate_and_authenticate(self, username: str, password: str) -> dict:
        user = self.authenticate_user(username, password)
        if not user:
            self.handle_failed_login(username)
            return {"success": False, "msg": "Credenciales inválidas", "code": "INVALID_CREDENTIALS", "status": 401}
        return {"success": True, "user": user}

    def build_token_pair(self, payload: dict, device_id: str) -> dict:
        payload["device_id"] = device_id
        access_token, refresh_token = self.auth_service.generate_tokens(payload=payload)
        return {"access_token": access_token, "refresh_token": refresh_token}

    def persist_user_token(self, user: UserModel, refresh_token: str, user_agent: dict, ip: str, is_admin: bool = False) -> dict:
        decoded = self.auth_service.get_token_payload(token=refresh_token)
        if is_admin or user.rol == "admin":
            return self.persist_refresh_token_admin(decoded, refresh_token, user_agent, ip)
        return self.persist_refresh_token(decoded, refresh_token, user_agent, ip)

    # ==============================================================
    # PERSISTENCIA DE TOKENS
    # ==============================================================
    def persist_refresh_token(self, decoded_token: dict, token: str, user_agent: dict, ip: str, refresh_attempts: int = 0) -> dict:
        return self.auth_service.upsert_new_token(
            username=decoded_token["sub"],
            device_id=decoded_token["device_id"],
            jti=decoded_token["jti"],
            refresh_token=token,
            refresh_attempts=refresh_attempts,
            user_agent=user_agent,
            ip_address=ip
        )

    def persist_refresh_token_admin(self, decoded_token: dict, token: str, user_agent: dict, ip: str, refresh_attempts: int = 0) -> dict:
        return self.auth_service.upsert_new_token(
            username=decoded_token["sub"],
            device_id=decoded_token["device_id"],
            jti=decoded_token["jti"],
            refresh_token=token,
            refresh_attempts=refresh_attempts,
            browser=user_agent.get("browser"),
            os=user_agent.get("os"),
            ip_address=ip
        )
