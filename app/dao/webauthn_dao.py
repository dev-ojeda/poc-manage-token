# app/auth/dao/webauthn_dao.py
import datetime
from typing import Optional

from app.core.base_dao import BaseDAO
from app.model.web_authn_credential_model import WebAuthnCredentialModel


class WebAuthnDAO(BaseDAO):
    """Acceso a datos WebAuthn en MongoDB."""

    COLLECTION = "credentials"

    def __init__(self, db=None, logger=None):
        super().__init__(db=db, collection_name=self.COLLECTION)
        self.logger = logger or self.logger.getChild("WebAuthnDAO")

    # ---------------------
    # Utilitarios
    # ---------------------
    @staticmethod
    def _now() -> datetime.datetime:
        return datetime.datetime.now(tz=datetime.timezone.utc)

    def _to_web_authn_credential_model(self, data: Optional[dict]) -> Optional[WebAuthnCredentialModel]:
        return WebAuthnCredentialModel.from_bson(data) if data else None

    def create_web_authn_credential(self, credential: WebAuthnCredentialModel) -> str:
        """Guarda una credencial WebAuthn en la colección."""
        credential.validate()
        existing = self.find_by_raw_id(raw_id=credential.raw_id)
        if existing:
            raise ValueError(f"rawId '{credential.raw_id}' ya existe")
        result = self.insert_one(doc=credential.to_bson(), context="Create Web Authn Credential")
        return str(result.inserted_id)

    def find_by_raw_id(self, raw_id: str) -> Optional[WebAuthnCredentialModel]:
        """Recupera una credencial por rawId."""
        res = self.find_one({"raw_id": raw_id}, context="Find Web Authn Credential by Raw_Id")
        if res:
            return self._to_web_authn_credential_model(data=res.get("data"))
        return None

    def find_by_username(self, username: str) -> list[WebAuthnCredentialModel]:
        """Recupera todas las credenciales de un usuario."""
        res = self.find_many({"username": username})
        docs = res.get("data") if isinstance(res, dict) else res
        return [WebAuthnCredentialModel.from_bson(d) for d in (docs or [])]

    def update(self, credential: WebAuthnCredentialModel) -> bool:
        """Actualiza una credencial existente."""
        result = self.update_one(
            {"rawId": credential.raw_id},
            {"$set": credential.to_dict()}
        )
        return result.modified_count > 0

    def update_sign_count(self, raw_id: str, new_sign_count: int, context="Update Sign Count") -> bool:
        """Actualiza una credencial existente."""
        query = {"raw_id": raw_id}
        update_doc = {
            "$set": {
                "sign_count": new_sign_count,
                "last_used_at": self._now()
            }
        }
        result = self.update_one(query=query,update=update_doc,context=context)
        return result["data"]["modified"]

    def delete(self, raw_id: str) -> bool:
        """Elimina una credencial por rawId."""
        result = self.delete_one({"rawId": raw_id})
        return result.deleted_count > 0
