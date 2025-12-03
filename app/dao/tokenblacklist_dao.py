import datetime
from datetime import timezone
from typing import Any, Optional, Dict

from app.utils.mongo_op import mongo_op
from app.core import BaseDAO
from app.logging_config import get_logger


class TokenBlacklistDAO(BaseDAO):
    COLLECTION = "token_blacklist"

    def __init__(self, db=None, logger=None):
        super().__init__(db=db, collection_name=self.COLLECTION)
        self.logger = logger or get_logger("TokenBlacklistDAO")

    # -------------------------------
    # Revocar token existente
    # -------------------------------
    def revoke_token(
        self,
        token: str,
        username: Optional[str] = None,
        device_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        update_fields = {"revoked_at": datetime.datetime.now(tz=timezone.utc)}
        if reason:
            update_fields["reason"] = reason
        if username:
            update_fields["username"] = username
        if device_id:
            update_fields["device_id"] = device_id

        return self.update_one(
            query={"token": token},
            update={"$set": update_fields},
            context="Revoke Token Blacklist"
        )

    # -------------------------------
    # Eliminar token de blacklist
    # -------------------------------
    def delete_token(self, token: str) -> Dict[str, Any]:
        return mongo_op.delete_one(self.collection, {"token": token}, context="Delete Token Blacklist")
