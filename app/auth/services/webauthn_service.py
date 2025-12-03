import base64
import os
from typing import Optional
from fido2.server import Fido2Server
from fido2.webauthn import AttestationObject, AttestedCredentialData, CollectedClientData, PublicKeyCredentialDescriptor, PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from app.config import Config
from app.core import BaseService
from app.dao.webauthn_dao import WebAuthnDAO
from app.model.web_authn_credential_model import WebAuthnCredentialModel
from app.logging_config import setup_logging

class WebAuthnCredentialService(BaseService[WebAuthnDAO]):
    dao: WebAuthnDAO

    def __init__(
        self, 
        db=None, 
        webauthn_dao: Optional[WebAuthnDAO] = None,
        web_authn_credential_model: Optional[WebAuthnCredentialModel] = None,
        logger=None
    ):
        super().__init__(db=db, dao=webauthn_dao, logger=logger)
        self.logger = logger or setup_logging().getChild(__class__.__name__)
        self.dao = webauthn_dao or WebAuthnDAO(db=self.db, logger=self.logger)
        self.web_authn_credential_model = web_authn_credential_model or WebAuthnCredentialModel()
        self.server = Fido2Server(PublicKeyCredentialRpEntity(name=Config.FIDO2_RP_NAME, id=Config.FIDO2_RP_ID))
    # -----------------
    # Base64 helpers
    # -----------------
    @staticmethod
    def _b64u_encode(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    @staticmethod
    def _b64u_decode(s: str) -> bytes:
        pad = "=" * ((4 - len(s) % 4) % 4)
        return base64.urlsafe_b64decode(s + pad)
    @staticmethod
    def _base64_to_base64url(b64: str) -> str:
        return b64.replace("+", "-").replace("/", "_").rstrip("=")

    def _serialize_bytes(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return self._b64u_encode(obj)
        if isinstance(obj, dict):
            return {k: self._serialize_bytes(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._serialize_bytes(v) for v in obj]
        return obj

    # -----------------
    # Registration
    # -----------------
    def register_credential(self, data: dict, username: str) -> str:
        """
        Verifica la attestation recibida del cliente, extrae la clave pública (pubkey)
        y guarda la credencial en MongoDB.
        """
        raw_id = data["cred"]["rawId"]
        attestation_object_b64 = data["cred"]["attestationObject"]
        client_data_json_b64 = data["cred"]["clientDataJSON"]
        
        if not all([raw_id, attestation_object_b64, client_data_json_b64]):
            raise ValueError("Datos WebAuthn incompletos")

        # Normaliza raw_id
        if isinstance(raw_id, str):
            raw_id_norm = raw_id.replace(" ", "").replace("\n", "")
        else:
            raw_id_norm = self._b64u_encode(raw_id)

        attestation_object = self._b64u_decode(attestation_object_b64)
        client_data_json = self._b64u_decode(client_data_json_b64)

        att_obj = AttestationObject(attestation_object)
        client_data = CollectedClientData(client_data_json)

        if client_data.type != "webauthn.create":
            raise ValueError("Tipo de operación inválido")

        # Extraer datos del autenticador
        auth_data = att_obj.auth_data
        cred_data: AttestedCredentialData = auth_data.credential_data

        # Clave pública serializada a formato COSE dict
        pubkey_cose = cred_data.public_key
        if not isinstance(pubkey_cose, dict):
            pubkey_cose = getattr(pubkey_cose, "_data", {})

        # Transformar bytes dentro del dict a Base64URL strings
        pubkey_cose_serializable = self._serialize_bytes(pubkey_cose)
   
        credential = WebAuthnCredentialModel(
            raw_id=raw_id_norm,
            type=data.get("type", "public-key"),
            attestation_object=attestation_object_b64,
            client_data_json=client_data_json_b64,
            username=username,
            origin="https://localhost:5000",
            device="unknown",
            fmt=att_obj.fmt,
            verified=True,
            pubkey=pubkey_cose_serializable,
            sign_count=0,
            user_handle=None,
        )

        self.logger.info(f"🔐 Credencial serializada: {credential.to_bson()}")
        return self._safe_exec(
            lambda: self.dao.create_web_authn_credential(credential=credential),
            context="Create WebAuthn Credential"
        )


    # -----------------
    # Authentication
    # -----------------
    def authenticate(self, assertion: dict) -> WebAuthnCredentialModel:
        """
        Verifica un login con la clave pública almacenada.
        Lanza ValueError si la firma no es válida.
        """
        cred: Optional[WebAuthnCredentialModel] = self._safe_exec(
            lambda: self.dao.find_by_raw_id(raw_id=assertion["id"]),
            context="Find WebAuthn Credential by Raw_Id",
        )
        if not cred:
            raise ValueError("Credencial no encontrada")
        verified = cred.verify_assertion(
            state=None, 
            client_data_json=assertion["response"]["clientDataJSON"], 
            authenticator_data=assertion["response"]["authenticatorData"], 
            signature=assertion["response"]["signature"]
        )
        if not verified:
            raise ValueError("Firma no válida")
        # Aquí puedes usar fido2 para verificar la firma (si guardas la clave pública)
        # Ejemplo futuro: cred.verify_assertion()

        return cred  # Placeholder hasta implementar verificación de firma
    
    def update_sign_count(self, raw_id: str, new_sign_count: int) -> bool:
        """
        Incrementa o actualiza el contador de firmas (sign_count)
        tras una autenticación exitosa.
        """
        return self._safe_exec(
            lambda: self.dao.update_sign_count(raw_id=raw_id, new_sign_count=new_sign_count),
            context="Update Sign Count"
        )

    # -----------------
    # Utilidades
    # -----------------
    def get_user_credentials(
        self, username: str
    ) -> list[PublicKeyCredentialDescriptor]:
        """Obtiene las credenciales registradas de un usuario en formato FIDO2."""
        creds = self._safe_exec(
            lambda: self.dao.find_by_username(username=username),
            context="Find WebAuthn credentials by username",
        )

        descriptors = []
        for c in creds or []:
            raw_id = c.raw_id
            raw_id_bytes = (
                self._b64u_decode(raw_id)
                if isinstance(raw_id, str)
                else raw_id
            )
            descriptors.append(
                PublicKeyCredentialDescriptor(id=raw_id_bytes, type="public-key")
            )
        return descriptors


    def get_registration_options(self, username: str):
        """Genera los parámetros de registro inicial (challenge + RP info)."""
        user_id = os.urandom(16)
        user = PublicKeyCredentialUserEntity(
            name=username, id=user_id, display_name=username
        )

        registration_data, state = self.server.register_begin(user=user)

        return {
            "publicKey": {
                "challenge": self._b64u_encode(registration_data.public_key.challenge),
                "rp": {
                    "name": registration_data.public_key.rp.name,
                    "id": registration_data.public_key.rp.id,
                },
                "user": {
                    "id": self._b64u_encode(user_id),
                    "name": username,
                    "displayName": username,
                },
                "pubKeyCredParams": [
                    {"type": "public-key", "alg": -7},
                    {"type": "public-key", "alg": -257},
                ],
                "timeout": getattr(
                    registration_data.public_key, "timeout", 60000
                ),
                "attestation": "none",
                "authenticatorSelection": {
                    "residentKey": "required",
                    "userVerification": "required",
                },
            }
        }, state

