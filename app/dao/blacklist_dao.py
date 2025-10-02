import datetime
from datetime import timezone
import logging
from typing import Any, Optional

from app.dao.base_dao import BaseDAO
from app.utils.db_mongo import MongoDatabase


class TokenBlacklistDAO(BaseDAO):
    def __init__(self, db: Optional[MongoDatabase] = None):
        super().__init__(db=db, collection_name="token_blacklist")
        self.logger = logging.getLogger(f"DAO.{self.__class__.__name__}")
    # -------------------------------
    # Verificar si un token está revocado
    # -------------------------------
    def is_token_revoked(self, jti: str) -> bool:
        try:
            count = self.count_documents({"jti": jti}).get("count", 0)
            return count > 0
        except Exception as e:
            self.logger.error(f"[is_token_revoked] Error: {e}")
            return False

    # -------------------------------
    # Insertar un token en blacklist
    # -------------------------------
    def insert_token(
        self,
        token: str,
        jti: Optional[str] = None,
        username: Optional[str] = None,
        device_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> dict[str, Any]:
        doc = {
            "token": token,
            "jti": jti,
            "revoked_at": None,
            "username": username,
            "device_id": device_id,
            "reason": reason,
            "created_at": datetime.datetime.now(tz=timezone.utc)
        }
        return self.insert_with_log(doc, context="Insert Token Blacklist")

   # -------------------------------
    # Revocar token existente
    # -------------------------------
    def revoke_token(
        self,
        token: str,
        username: Optional[str] = None,
        device_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> dict[str, Any]:
        update_fields = {
            "revoked_at": datetime.datetime.now(tz=timezone.utc)
        }
        if reason:
            update_fields["reason"] = reason
        if username:
            update_fields["username"] = username
        if device_id:
            update_fields["device_id"] = device_id

        return self.update_with_log(
            query={"token": token},
            update={"$set": update_fields},
            upsert=True,
            context="Revoke Token Blacklist"
        )

    # -------------------------------
    # Eliminar token de blacklist
    # -------------------------------
    def delete_token(self, token: str) -> dict[str, Any]:
        return self.delete_one({"token": token}, context="Delete Token Blacklist")