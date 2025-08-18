# app/services/auth_service.py

from datetime import datetime, timezone
from app.dao.auth_dao import AuthDao
from app.utils.db_manager import DbManager
from app.model.token_generator import TokenGenerator

class AuthService:
    def __init__(self):
        self.dm = DbManager()
        self.gt = TokenGenerator()
        self.auth_dao = AuthDao()
    def get_token_payload(self, token: str):
        return self.gt.verify_token(token=token, expected_type="refresh")

    def get_active_token_by_user(self, username, device_id=None):
        return self.auth_dao.get_active_token_by_user(username, device_id)
    def revoke_all_tokens_for_user(self, username):
        return self.auth_dao.revoke_all_tokens_for_user(username)
    def revoke_token_by_jti(self, jti):
        return self.auth_dao.revoke_token_by_jti(jti)
    def revoke_token_by_device_id(self, device_id):
        return self.auth_dao.revoke_token_by_device_id(device_id)
    def is_token_expired(self, payload: dict) -> bool:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        return now_ts > payload.get("exp", 0)

    def detect_reuse(self, stored: dict) -> bool:
        return stored.get("used_at") is not None

    def device_mismatch(self, stored: dict, device_id: str) -> bool:
        return str(stored.get("device_id", "")).strip() != device_id

    def mark_used(self, **kwargs) -> bool:
        return self.auth_dao.mark_token_as_used(**kwargs)

    def revoke_old_token(self, username, device_id, token) -> bool:
        return self.dm.revoke_refresh_token(username, device_id, token)

    def is_valid_refresh(self, token, device_id) -> bool:
        return self.dm.is_valid_refresh_token(token, device_id)

    def upsert_new_token(self, **kwargs) -> dict:
        return self.dm.upsert_refresh_token(**kwargs)

    def get_refresh_token_from_db(self, token: str) -> dict | None:
        return self.dm.get_refresh_token(token)

    def revoke_all_for_device(self, device_id: str):
        return self.dm.revoke_tokens_by_device(device_id)

    def generate_tokens(self, payload: dict) -> tuple[str, str]:
        return self.gt.create_tokens(payload)

    def verify_access_token(self, token: str):
        return self.gt.verify_token(token, expected_type="access")
