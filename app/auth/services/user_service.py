# app/auth/services/user_service.py
from datetime import datetime, timedelta
from typing import Optional, List

from app.core.base_service import BaseService
from app.model.user_model import UserModel
from app.dao.user_dao import UserDAO
from app.auth import get_auth_services


class UserService(BaseService[UserDAO]):
    """
    Servicio de gestión de usuarios.
    Maneja login, intentos fallidos, bloqueo y consultas de usuario.
    Hereda BaseService para logging y DAO.
    """

    MAX_ATTEMPTS = 3
    BLOCK_TIME_SECONDS = 120  # 2 minutos
    dao = UserDAO
    def __init__(self, db=None, user_dao: Optional[UserDAO] = None, logger=None):
        super().__init__(db=db, dao=user_dao, logger=logger)
        self.dao = user_dao or UserDAO(db=self.db, logger=self.logger)
    # ==========================
    # LOGIN PRINCIPAL
    # ==========================
    def get_user_login(
        self,
        username: str,
        password: str,
        device_id: str,
        user_agent: dict,
        ip: str
    ) -> dict:
        try:
            user: UserModel = self.get_user_by_username(username)
            if not user:
                return self._user_not_found(username)

            blocked_status = self.is_user_blocked(username)
            if not blocked_status["success"]:
                return blocked_status

            auth_result = self.validate_and_authenticate(username, password)
            if not auth_result["success"]:
                return auth_result

            user = auth_result["user"]
            self.reset_login_attempts(user)

            # Tokens
            auth_service = get_auth_services().auth_service
            access_token, refresh_token = auth_service.generate_tokens({
                "username": username,
                "device_id": device_id,
                "rol": user.rol,
            })
            decoded = auth_service.get_token_payload(token=refresh_token)

            persisted = auth_service.upsert_new_token(
                username=decoded.sub,
                device_id=device_id,
                jti=decoded.jti,
                refresh_token=refresh_token,
                refresh_attempts=0,
                user_agent=user_agent,
                ip_address=ip
            )
            if not persisted.get("success", True):
                self.logger.error("Error al persistir token")
                return self._error_response("TOKEN_PERSIST_FAIL", "Error al persistir token", 500)

            return {
                "success": True,
                "data": user.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "status": 200
            }

        except Exception as e:
            self.logger.exception(f"Error autenticando usuario: {e}")
            return self._error_response("LOGIN_ERROR", "Error interno", 500)

    # ==========================
    # CONSULTAS
    # ==========================
    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        return self._safe_exec(lambda: self.dao.find_by_username(username=username),context="Get by UserName")

    def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        return self._safe_exec(lambda: self.dao.find_by_id(user_id=user_id), context="Get User by ID")

    def get_all_users(self) -> List[dict]:
        return self._safe_exec(lambda: self.dao.get_all_users(), context="Get All Users")

    # ==========================
    # LOGIN & AUTENTICACIÓN
    # ==========================
    def authenticate_user(self, username: str, password: str) -> Optional[UserModel]:
        user = self.get_user_by_username(username)
        if user and UserModel.verify_password(password, user.password):
            return user
        return None

    def validate_and_authenticate(self, username: str, password: str) -> dict:
        user = self.authenticate_user(username, password)
        if not user:
            self.handle_failed_login(username)
            return self._error_response("INVALID_CREDENTIALS", "Credenciales inválidas", 401)
        return {"success": True, "user": user}

    # ==========================
    # INTENTOS FALLIDOS Y BLOQUEO
    # ==========================
    def handle_failed_login(self, username: str) -> dict:
        user = self.get_user_by_username(username)
        if not user:
            return self._user_not_found(username)

        attempts = user.failed_attempts + 1
        update_fields = {"failed_attempts": attempts}

        if attempts >= self.MAX_ATTEMPTS:
            update_fields.update({
                "blocked_until": self._blocked_until(),
                "failed_attempts": 0
            })

        return self._safe_exec(
            lambda: self.dao.update_one(query={"username": user.username, "rol": user.role},update={"$set": update_fields}),
            upsert=True,
            context="Intentos Fallidos"
        )

    def reset_login_attempts(self, user: UserModel) -> dict:
        return self._safe_exec(lambda: self.dao.reset_login_attempts(user=user),context="Reset Login Attempts")

    def _blocked_until(self) -> datetime:
        return self.now() + timedelta(seconds=self.BLOCK_TIME_SECONDS)

    # ==========================
    # BLOQUEO
    # ==========================
    def is_user_blocked(self, username: str) -> dict:
        user = self.get_user_by_username(username)
        if not user:
            return self._user_not_found(username)

        if user.blocked_until and user.blocked_until > self.now():
            return {
                "success": False,
                "msg": "⏳ Usuario temporalmente bloqueado",
                "bloqueado_hasta": user.blocked_until.timestamp(),
                "code": "USER_BLOCKED",
                "status": 403
            }
        return {"success": True, "msg": "Usuario activo", "code": "USER_ACTIVE", "status": 200}

    # ==========================
    # HELPERS
    # ==========================
    def _user_not_found(self, username: str) -> dict:
        return {"success": False, "msg": f"Usuario '{username}' no encontrado", "code": "INVALID_USER", "status": 404}

    def _error_response(self, code: str, msg: str, status: int) -> dict:
        return {"success": False, "msg": msg, "code": code, "status": status}

    def validate_login_payload(self, data: dict) -> List[str]:
        required_fields = ['username', 'password', 'device', 'rol', 'user_agent']
        return [field for field in required_fields if not data.get(field)]
