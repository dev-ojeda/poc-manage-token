from typing import Optional, Dict, Any
from app.core.base_service import BaseService
from app.dao.tokenblacklist_dao import TokenBlacklistDAO


class TokenBlacklistService(BaseService):
    """
    Servicio para manejar tokens en la blacklist.
    Hereda BaseService para logging y manejo seguro de errores.
    """

    dao: Optional[TokenBlacklistDAO] = None

    def __init__(self, db=None, logger=None, dao: Optional[TokenBlacklistDAO] = None):
        super().__init__(db=db, dao=dao, logger=logger)
        self.dao = dao or TokenBlacklistDAO()

    # --------------------------
    # Revocar token
    # --------------------------
    def revoke_token_blacklist(
        self,
        token: str,
        device_id: Optional[str] = None,
        username: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoca un token y lo registra en la blacklist.
        """
        return self._safe_exec(
            lambda: self.dao.revoke_token(
            token=token,
            device_id=device_id,
            username=username,
            reason=reason),
            context="revoke_token_blacklist"
        )
