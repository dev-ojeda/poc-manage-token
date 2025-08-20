# app/services/user_service.py

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from bson import ObjectId


from app.dao.auth_dao import AuthDao
from app.utils.db_manager import DbManager
from app.model.user import User
from app.dao.user_dao import UserDAO


class UserService:
    def __init__(self):
        self.MAX_ATTEMPTS = 3
        self.BLOCK_TIME_SECONDS = 120  # 2 min
        self.auth_dao = AuthDao()
        self.user_dao = UserDAO()
    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.user_dao.find_by_username(username)

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.user_dao.find_by_id(user_id=user_id)
    def get_ids_users (self) -> List[ObjectId]:
        return self.user_dao.find_ids_users()

    def validate_login_payload(self, data: dict) -> list:
        required_fields = ['username', 'password', 'device', 'rol', 'user_agent']
        return [f for f in required_fields if not data.get(f)]

    def authenticate_user(self, username: str, password: str) -> User:
        user = self.user_dao.find_by_username(username)
        if user and User.verify_password(password, user.password):
            return user
        return None

    def handle_failed_login(self, user_model: User) -> dict:
        attempts = user_model.failed_attempts + 1
        update = {"$set": {"failed_attempts": attempts}}

        if attempts >= self.MAX_ATTEMPTS:
            update["$set"]["blocked_until"] = datetime.now(timezone.utc) + timedelta(seconds=self.BLOCK_TIME_SECONDS)
            update["$set"]["failed_attempts"] = 0

        return self.user_dao.update({"username": user_model.username, "rol": user_model.rol}, update, upsert=True, context="Intentos Fallidos")

    def reset_login_attempts(self, user_model: User) -> dict:
        return self.user_dao.update({"username": user_model.username, "rol": user_model.rol}, {
            "$set": {"failed_attempts": 0, "blocked_until": None}
        }, upsert=True, context="Reset Intentos")

    def persist_refresh_token(self, decoded_token: dict, token: str, user_agent: dict, ip: str, refresh_attempts=0) -> dict:
        return self.auth_dao.update_refresh_token(
            username=decoded_token["sub"],
            device_id=decoded_token["device_id"],
            jti=decoded_token["jti"],
            refresh_token=token,
            refresh_attempts=refresh_attempts,
            user_agent=user_agent,
            ip_address=ip
        )

    def persist_refresh_token_admin(self, decoded_token: dict, token: str, user_agent: dict, ip: str, refresh_attempts=0) -> dict:
        return self.auth_dao.update_refresh_token(
            username=decoded_token["sub"],
            device_id=decoded_token["device_id"],
            jti=decoded_token["jti"],
            refresh_token=token,
            refresh_attempts=refresh_attempts,
            user_agent=user_agent,
            ip_address=ip
        )

    