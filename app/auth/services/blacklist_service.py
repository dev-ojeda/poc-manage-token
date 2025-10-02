from typing import Optional, Dict, Any
from app.dao.blacklist_dao import TokenBlacklistDAO


class TokenBlacklistService:
    """
    Servicio para manejar tokens en la blacklist.
    """

    def __init__(self):
        self.blacklist_dao = TokenBlacklistDAO()

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
        return self.blacklist_dao.revoke_token(
            token=token,
            device_id=device_id,
            username=username,
            reason=reason
        )
