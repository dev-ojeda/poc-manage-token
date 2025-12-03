from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from app.dao.auth_dao import AuthDAO
from app.helpers.token_doc import TokenDoc
from app.model.token_generator_model import TokenGeneratorModel
from app.model.token_model import TokenModel
from app.core.base_service import BaseService
from app.model.web_authn_credential_model import WebAuthnCredentialModel


class AuthService(BaseService[AuthDAO]):
    """
    Servicio para manejar autenticación y gestión de tokens.
    Refactorizado sobre BaseService para logging, safe_exec y consistencia.
    """

    dao: AuthDAO

    def __init__(
        self,
        db=None,
        auth_dao: Optional[AuthDAO] = None,
        token_generator: Optional[TokenGeneratorModel] = None,
        logger=None
    ):
        super().__init__(db=db, dao=auth_dao, logger=logger)
        self.dao = auth_dao or AuthDAO(db=self.db, logger=self.logger)
        self.token_generator = token_generator or TokenGeneratorModel()

    # -------------------------------
    # Token verification
    # -------------------------------
    def get_token_payload(self, token: str, expected_type: str = "refresh") -> TokenModel:
        return self._safe_exec(
            lambda: self.token_generator.verify_token(
            token=token,
            expected_type=expected_type),
            context="verify_token"
        )

    def verify_access_token(self, token: str) -> TokenModel:
        return self.get_token_payload(token, expected_type="access")

    # -------------------------------
    # Token generation
    # -------------------------------
    def generate_tokens(self, payload: Dict[str, Any]) -> Tuple[str, str]:
        return self._safe_exec(lambda: self.token_generator.create_tokens(data=payload),context="generate_tokens")

    def decode_refresh_token(self, token: str) -> Optional[TokenDoc]:
        return self._safe_exec(lambda: self.token_generator.get_refresh_access_token(refresh_token=token),context="decode_refresh_token")

    # -------------------------------
    # Refresh token management
    # -------------------------------
    def get_active_token_by_user_and_device(self, username: str, device_id: str) -> Optional[Dict]:
        return self._safe_exec(lambda: self.dao.get_active_token_by_user_and_device(username=username,device_id=device_id),context="get_active_token_by_user_and_device"
        )

    def get_active_token_by_username(self, username: str) -> Optional[dict]:
        return self._safe_exec(lambda: self.dao.get_active_token_by_username(username=username),context="get_active_token_by_username")

    def is_token_in_use(self, username: str) -> bool:
        return bool(self._safe_exec(lambda: self.dao.is_token_in_use(username=username), context="is_token_in_use"))

    def get_refresh_token(self, refresh_token: str) -> Optional[Dict]:
        return self._safe_exec(lambda: self.dao.get_refresh_token(refresh_token=refresh_token), context="get_refresh_token")

    def is_valid_refresh(self, token: str, device_id: str) -> bool:
        return bool(self._safe_exec(lambda: self.dao.is_valid_refresh_token(refresh_token=token,device_id=device_id), context="is_valid_refresh"))

    def upsert_new_token(self, **kwargs) -> Dict:
        return self._safe_exec(lambda: self.dao.upsert_refresh_token(**kwargs),context="upsert_new_token")

    def revoke_old_token(self, username: str, token: str, jti: str, upsert: bool = False) -> Dict:
        return self._safe_exec(lambda: 
            self.dao.revoke_old_token(
            username=username,
            refresh_token=token,
            jti=jti),
            upsert=upsert,
            context="revoke_old_token"
        )

    # -------------------------------
    # Token revocation
    # -------------------------------
    def revoke_all_tokens_for_user(self, username: str) -> Dict:
        return self._safe_exec(lambda: self.dao.revoke_all_tokens_for_user(username), context="revoke_all_tokens_for_user")

    def revoke_token_by_jti(self, jti: str) -> Dict:
        return self._safe_exec(lambda: self.dao.revoke_token_by_jti(jti=jti), context="revoke_token_by_jti")

    def revoke_token_by_device_id(self, device_id: str) -> bool:
        return bool(self._safe_exec(lambda: self.dao.revoke_token_by_device_id(device_id=device_id), context="revoke_token_by_device_id"))

    # -------------------------------
    # Token checks & updates
    # -------------------------------
    @staticmethod
    def is_token_expired(exp: float) -> bool:
        return datetime.now(tz=timezone.utc).timestamp() > exp

    @staticmethod
    def detect_reuse(stored: Optional[Dict]) -> bool:
        return bool(stored and stored.get("used_at"))

    @staticmethod
    def device_mismatch(stored: Optional[Dict], device_id: str) -> bool:
        return str(stored.get("device_id", "")).strip() != device_id

    def mark_used(self, **kwargs) -> bool:
        return bool(self._safe_exec(lambda: self.dao.mark_token_as_used(**kwargs), context="mark_token_used"))

    def register_credential(self, credential: WebAuthnCredentialModel) -> str:
        """Verifica y guarda la credencial."""
        if credential.verify_attestation(rp_id="localhost", origin="http://localhost:5000"):
            return self._safe_exec(lambda: self.dao.save(credential=credential), context="register_credential")
        raise ValueError("Attestation inválido")