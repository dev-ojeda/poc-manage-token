import base64
import os
import re
from dataclasses import dataclass, field, asdict
from bson import Binary, ObjectId
from datetime import datetime, timezone
from typing import ClassVar, Optional, Any

from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialDescriptor, PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from fido2.cose import CoseKey

from app.config import Config

@dataclass
class WebAuthnCredentialModel:
    """Modelo WebAuthn persistente y verificable en MongoDB."""

    raw_id: Optional[str] = None
    type: str = "public-key"
    attestation_object: Optional[str] = None
    client_data_json: Optional[str] = None
    username: str = "anon"
    origin: str = "unknown"
    device: str = "unknown"
    fmt: Optional[str] = None
    sign_count: int = 0
    verified: bool = False
    pubkey: Optional[dict] = field(default_factory=dict)
    user_handle: Optional[str] = None

    _id: ObjectId = field(default_factory=ObjectId)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    
    BASE64URL_REGEX: ClassVar[str] = r"^[A-Za-z0-9\-_]+={0,2}$"



    # -----------------------------
    # Validación
    # -----------------------------
    def validate(self) -> None:
        if not self.raw_id or not isinstance(self.raw_id, str):
            raise ValueError("raw_id es obligatorio y debe ser string")
        if not re.match(self.BASE64URL_REGEX, self.raw_id):
            raise ValueError("raw_id debe ser Base64URL válido")
        if self.type != "public-key":
            raise ValueError("type debe ser 'public-key'")
        if not (self.attestation_object and self.client_data_json):
            raise ValueError("attestationObject y clientDataJSON son requeridos")
        if not isinstance(self.pubkey, dict):
            raise ValueError("pubkey debe ser un objeto COSE válido")

    # -----------------------------
    # Serialización
    # -----------------------------
    def to_bson(self) -> dict:
        """Convierte el modelo WebAuthn a documento BSON listo para MongoDB."""
        doc = asdict(self)
        doc["_id"] = self._id if hasattr(self, "_id") else ObjectId()

        def to_binary(value):
            if value is None:
                return None
            if isinstance(value, (bytes, bytearray)):
                return Binary(value)
            return value

        # Convertir campos binarios a Binary
        for key in [
            "raw_id",
            "attestation_object",
            "client_data_json",
            "public_key",
            "user_handle",
        ]:
            if key in doc:
                doc[key] = to_binary(doc[key])

        # Normalizar pubkey
        if doc.get("pubkey"):
            doc["pubkey"] = {str(k): v for k, v in doc["pubkey"].items()}

        # Eliminar None explícitos
        clean_doc = {k: v for k, v in doc.items() if v is not None}

        return clean_doc


    @staticmethod
    def from_bson(data: dict) -> "WebAuthnCredentialModel":
        if not data:
            raise ValueError("Documento BSON vacío o inválido")

        def to_bytes(value):
            """Convierte Binary o base64url string a bytes."""
            if value is None:
                return None
            if isinstance(value, Binary):
                return bytes(value)
            if isinstance(value, bytes):
                return value
            if isinstance(value, str):
                return base64.urlsafe_b64decode(value + "==")
            raise TypeError(f"Tipo no soportado: {type(value)}")

        pubkey = data.get("pubkey", {})
        if pubkey:
            pubkey = {str(k): v for k, v in pubkey.items()}

        return WebAuthnCredentialModel(
            raw_id=to_bytes(data.get("rawId") or data.get("raw_id")),
            type_=data.get("type", "public-key"),  # evita shadowing
            attestation_object=to_bytes(
                data.get("attestationObject") or data.get("attestation_object")
            ),
            client_data_json=to_bytes(
                data.get("clientDataJSON") or data.get("client_data_json")
            ),
            username=data.get("username", "anon"),
            origin=data.get("origin", "unknown"),
            device=data.get("device", "unknown"),
            fmt=data.get("fmt"),
            sign_count=int(data.get("sign_count", 0)),
            verified=bool(data.get("verified", False)),
            pubkey=pubkey,
            user_handle=to_bytes(data.get("user_handle")),
            _id=data.get("_id", ObjectId()),
            created_at=data.get("created_at", datetime.now(tz=timezone.utc)),
        )

    # -----------------------------
    # Verificación WebAuthn
    # -----------------------------
    def verify_assertion(
        self,
        state: Any,
        client_data_json: bytes,
        authenticator_data: bytes,
        signature: bytes,
    ) -> bool:
        """Verifica un assertion WebAuthn usando la clave pública almacenada."""
        try:
            # Normaliza claves string → int para COSE
            cose_data = {
                int(k): v for k, v in self.pubkey.items()
                if isinstance(k, str) and re.match(r"^-?\d+$", k)
            }

            cose_key = CoseKey.from_dict(cose_data)

            credential_descriptor = PublicKeyCredentialDescriptor(
                id=self.raw_id.encode() if isinstance(self.raw_id, str) else self.raw_id,
                type=self.type,
            )

            result = self.server.authenticate_complete(
                state=state,
                credentials=[{
                    "type": self.type,
                    "id": credential_descriptor.id,
                    "public_key": cose_key,
                    "sign_count": self.sign_count,
                }],
                credential_id=credential_descriptor.id,
                client_data_json=client_data_json,
                authenticator_data=authenticator_data,
                signature=signature,
            )

            if hasattr(result, "new_sign_count"):
                self.sign_count = result.new_sign_count

            self.verified = True
            return True

        except Exception as e:
            print(f"❌ Error de verificación WebAuthn: {e}")
            self.verified = False
            return False

  