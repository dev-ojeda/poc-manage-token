import datetime
from datetime import timezone
from typing import Optional, Tuple

from app.dao.auth_dao import AuthDAO
from app.hekpers.token_doc import TokenDoc
from app.model.token_generator_model import TokenGeneratorModel


class AuthService:
    """
    Servicio para manejar autenticación, tokens de acceso y refresh tokens.
    """

    def __init__(self):
        self.auth_dao = AuthDAO()
        self.token_generator_model = TokenGeneratorModel()

    # -------------------------------
    # Token verification
    # -------------------------------
    def get_token_payload(self, token: str, expected_type: str = "refresh") -> dict:
        return self.token_generator_model.verify_token(token=token, expected_type=expected_type)

    def verify_access_token(self, token: str) -> dict:
        return self.token_generator_model.verify_token(token, expected_type="access")

    # -------------------------------
    # Token generation
    # -------------------------------
    def generate_tokens(self, payload: dict) -> Tuple[str, str]:
        return self.token_generator_model.create_tokens(payload)

    def decode_refresh_token(self, token: str) -> TokenDoc | None:
        return self.token_generator_model.get_refresh_access_token(refresh_token=token)

    # -------------------------------
    # Refresh token management
    # -------------------------------
    def get_active_token_by_user_and_device(self, username: str, device_id: str) -> Optional[dict]:
        return self.auth_dao.get_active_token_by_user_and_device(username=username, device_id=device_id)

    def get_active_token_by_username(self, username: str) -> Optional[dict]:
        return self.auth_dao.get_active_token_by_username(username)

    def is_token_in_use(self, username: str) -> dict:
        return self.auth_dao.is_token_in_use(username)

    def get_refresh_token(self, refresh_token: str) -> Optional[dict]:
        return self.auth_dao.get_refresh_token(refresh_token=refresh_token)

    def is_valid_refresh(self, token: str, device_id: str) -> bool:
        return self.auth_dao.is_valid_refresh_token(token, device_id)

    def upsert_new_token(self, **kwargs) -> dict:
        return self.auth_dao.upsert_refresh_token(**kwargs)

    def revoke_old_token(self, username: str, token: str, jti: str, upsert: bool) -> dict:
        return self.auth_dao.revoke_old_token(username=username, refresh_token=token, jti=jti, upsert=upsert)

    # -------------------------------
    # Token revocation
    # -------------------------------
    def revoke_all_tokens_for_user(self, username: str) -> dict:
        return self.auth_dao.revoke_all_tokens_for_user(username)

    def revoke_token_by_jti(self, jti: str) -> dict:
        return self.auth_dao.revoke_token_by_jti(jti)

    def revoke_token_by_device_id(self, device_id: str) -> bool:
        return bool(self.auth_dao.revoke_token_by_device_id(device_id))

    # -------------------------------
    # Token checks & updates
    # -------------------------------
    @staticmethod
    def is_token_expired(exp: float) -> bool:
        return datetime.datetime.now(tz=timezone.utc).timestamp() > exp

    @staticmethod
    def detect_reuse(stored: dict) -> bool:
        return bool(stored and stored.get("used_at"))

    @staticmethod
    def device_mismatch(stored: dict, device_id: str) -> bool:
        return str(stored.get("device_id", "")).strip() != device_id

    def mark_used(self, **kwargs) -> bool:
        return self.auth_dao.mark_token_as_used(**kwargs)
