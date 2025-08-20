from datetime import datetime, timezone

from app.utils.db_mongo import MongoDatabase

class TokenBlacklistDao:
    def __init__(self, db=None):
        self.db = db or MongoDatabase()
        # Si es mongomock o un Database de pymongo, exponemos la colección
        if hasattr(self.db, "__getitem__"):
            self.collection = self.db["token_blacklist"]
        else:
            self.collection = None
        self.token_blacklist = "token_blacklist"

    def is_token_revoked(self, jti: str) -> bool:
        return self.db.count_documents(self.token_blacklist,{"jti": jti}) > 0

    def insert_token(self, token: str, username: str = None, device_id: str = None, reason: str = None) -> bool:
        """
        Inserta un nuevo token.
        """
        doc = {
            "token": token,
            "revoked_at": None,
            "username": username,
            "device_id": device_id,
            "reason": reason,
            "created_at": datetime.now(timezone.utc)
        }
        try:
            self.collection.insert_one(doc)
            return True
        except Exception as e:
            print(f"Error insertando token: {e}")
            return False

    def revoke_token_blacklist(self, token: str, device_id=None, username=None, reason=None) -> dict:
        update_fields = {
            "revoked_at": datetime.fromisoformat(datetime.now(timezone.utc).isoformat())
        }

        if reason is not None:
            update_fields["reason"] = reason
        if device_id is not None:
            update_fields["device_id"] = device_id
        if username is not None:
            update_fields["username"] = username

        return self.db.update_with_log(
            self.token_blacklist,
            {"token": token},
            {"$set": update_fields},
            upsert=True,
            context="Revocar Token Blacklist"
        )
  
    def delete_token(self, token: str) -> bool:
        """
        Elimina un token de la colección.
        """
        result = self.collection.delete_one({"token": token})
        return result.deleted_count > 0
