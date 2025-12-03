from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from bson import SON
from app.core.base_dao import BaseDAO
from app.dao.session_dao import SessionDAO
from app.dao.auditlog_dao import AuditLogDAO
from app.logging_config import get_logger
from app.model.web_authn_credential_model import WebAuthnCredentialModel


class AuthDAO(BaseDAO):
    """
    DAO para manejar refresh tokens y autenticación.
    Hereda BaseDAO para logging y manejo centralizado de CRUD.
    """
    COLLECTION = "refresh_tokens"

    def __init__(self, db=None, logger=None):
        super().__init__(db=db, collection_name=self.COLLECTION)
        self.logger = logger or get_logger("AuthDAO")
        self.session_dao = SessionDAO(db=db, logger=self.logger)
        self.audit_dao = AuditLogDAO(db=db, logger=self.logger)
        

    # -----------------------------
    # Utils internos
    # -----------------------------
    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=timezone.utc)

    # -----------------------------
    # Consultas de tokens
    # -----------------------------
    def get_active_token_by_user_and_device(self, username: str, device_id: Optional[str] = None) -> Dict:
        match_filter = {"username": username, "revoked_at": None, "expires_at": {"$gt": self._now()}}
        if device_id:
            match_filter["device_id"] = device_id
        pipeline = [{"$match": match_filter}, {"$sort": SON([("created_at", -1)])}, {"$limit": 1}]
        return self.aggregate(pipeline, context="Get Active Token by User and Device")

    def get_active_token_by_username(self, username: str) -> dict:
        now = self._now()
        pipeline = [
            {"$match": {
                "username": username,
                "revoked_at": None,
                "expires_at": {"$gt": now}
            }},
            {"$sort": {"created_at": -1}},
            {"$limit": 1},
            {"$project": {
                "_id": 1,
                "username": 1,
                "device_id": 1,
                "jti": 1,
                "refresh_token": 1,
                "created_at": 1,
                "expires_at": 1,
                "revoked_at": 1,
                "used_at": 1
            }}
        ]
        return self.aggregate(pipeline, context="Get Active Token by Username")

    def get_refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        return self.find_one({"refresh_token": refresh_token}, context="Get Refresh Token")

    def is_valid_refresh_token(self, refresh_token: str, device_id: str) -> Dict[str, Any]:
        query = {"refresh_token": refresh_token, "device_id": device_id, "expires_at": {"$gt": self._now()}}
        token = self.find_one(query, context="Validate Refresh Token")
        valid = bool(token.get("data")) and not token.get("data", {}).get("revoked_at")
        return {"success": True, "data": valid}

    def is_token_in_use(self, username: str) -> Dict[str, Any]:
        query = {"username": username, "used_at": {"$ne": None}}
        projection = {"_id": 1, "username": 1, "device_id": 1, "refresh_token": 1, "jti": 1, "expires_at": 1}
        return self.find_one(query, projection, context="Check Token Usage")

    # -----------------------------
    # Revocación y actualización
    # -----------------------------
    def revoke_tokens(self, query_filter: dict, context: str = "Revoke Tokens") -> Dict[str, Any]:
        update = {"$set": {"revoked_at": self._now()}}
        return self.update_one(query_filter, update, context=context)

    def revoke_old_token(self, username: str, refresh_token: str, jti: str) -> Dict[str, Any]:
        now = self._now()
        query = {"username": username, "refresh_token": refresh_token, "jti": jti}
        update = {"$set": {"revoked_at": now, "used_at": now}}
        return self.update_one(query, update, context="Revoke Old Token")

    def revoke_token_by_jti(self, jti: str) -> Dict[str, Any]:
        return self.update_one({"jti": jti, "revoked_at": None}, context="Revoke Token by JTI")

    def revoke_token_by_device_id(self, device_id: str) -> Dict[str, Any]:
        return self.update_one({"device_id": device_id}, context="Revoke Token by Device ID")

    def mark_token_as_used(self, username: str, device_id: str, jti: str, refresh_token: str) -> Dict[str, Any]:
        now = self._now()
        query = {"username": username, "device_id": device_id, "jti": jti, "refresh_token": refresh_token}
        update = {"$set": {"revoked_at": now, "used_at": now}}
        return self.update_one(query, update, context="Mark Token Used")

    def upsert_refresh_token(
        self,
        **kwargs
    ) -> Dict[str, Any]:
        """Upsert de token de refresh, con auditoría de sesión previa."""
        # Intentar auditar la sesión previa, pero no bloquear el upsert
        try:
            previous_session = self.session_dao.find_previous_session(username=kwargs["username"], device_id=kwargs["device_id"])
            if previous_session.get("data"):
                self.audit_dao.insert_event_audit(
                    previous_session=previous_session["data"],
                    username=kwargs["username"],
                    device_id=kwargs["device_id"],
                    jti=kwargs["device_id"],
                    refresh_token=kwargs["refresh_token"],
                    refresh_attempts=kwargs["refresh_attempts"],
                    user_agent=kwargs["user_agent"],
                    ip_address=kwargs["ip_address"]
                )
        except Exception as audit_err:
            self.logger.warning(f"Fallo auditoría de sesión previa: {audit_err}")

        
        # Ejecutar upsert
        return self.upsert_token(**kwargs)

    # -----------------------------
    # WebAuth
    # -----------------------------

    def save(self, credential: WebAuthnCredentialModel) -> str:
        """Guarda una credencial WebAuthn en la colección."""
        credential.validate()
        existing = self.find_one({"rawId": credential.raw_id})
        if existing:
            raise ValueError(f"rawId '{credential.raw_id}' ya existe")
        result = self.insert_one(credential.to_dict())
        return str(result.inserted_id)

