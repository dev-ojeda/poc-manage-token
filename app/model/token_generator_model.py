import datetime
from datetime import timedelta, timezone
import uuid
from cryptography.hazmat.primitives import serialization
import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    ImmatureSignatureError,
    InvalidTokenError,
    InvalidSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
)

from app.config import Config
from app.auth.exceptions.auth_exceptions import AuthException
from app.model.token_model import TokenModel

class TokenGeneratorModel:
    def __init__(self):
        self.cfg = Config
        self.access_exp = int(self.cfg.ACCESS_TOKEN_EXP_MINUTES)
        self.access_exp_admin = int(self.cfg.ACCESS_TOKEN_EXP_ADMIN)
        self.refresh_exp = int(self.cfg.REFRESH_TOKEN_EXP_DAYS)
        self.refresh_exp_admin = int(self.cfg.REFRESH_TOKEN_EXP_ADMIN)
        self.access_exp_global = int(self.cfg.ACCESS_TOKEN_GLOBAL_EXP_SECONDS)
        self.valid_roles = self.cfg.VALID_ROLES
        self.roles_scope = self.cfg.ROLE_SCOPES
        self.jwt_issuer = self.cfg.JWT_ISSUER
        self.jwt_audience = self.cfg.JWT_AUDIENCE
        self.private_key = self._load_key(self.cfg.PATH_PRIVATE_KEY, is_private=True)
        self.public_key = self._load_key(self.cfg.PATH_PUBLIC_KEY, is_private=False)

     # -----------------------------
    # Key loading
    # -----------------------------
    def _load_key(self, path: str, is_private=False):
        try:
            with open(path, "rb") as f:
                key_data = f.read()
            return (
                serialization.load_pem_private_key(key_data, password=None)
                if is_private
                else serialization.load_pem_public_key(key_data)
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"Clave {'privada' if is_private else 'pública'} no encontrada en {path}")

    # -----------------------------
    # Payload builders
    # -----------------------------
    def _timestamp(self):
        return datetime.datetime.now(tz=timezone.utc)

    def _is_valid_role(self, role) -> bool:
        return role in self.valid_roles

    def _build_payload(self, data: dict, token_type: str, exp_value: int) -> dict:
        now = self._timestamp()
        exp = now + (timedelta(days=exp_value) if token_type == "refresh" else timedelta(minutes=exp_value))
        return {
            "sub": data["username"],
            "iat": now.timestamp(),
            "nbf": now.timestamp(),
            "exp": int(exp.timestamp()),
            "iss": self.cfg.JWT_ISSUER,
            "aud": self.cfg.JWT_AUDIENCE,
            "token_type": token_type,
            "jti": data.get("jti", str(uuid.uuid4())),
            "rol": data.get("rol"),
            "scope": data.get("scope"),
            "device_id": data.get("device_id"),
        }

    # -----------------------------
    # Token creation
    # -----------------------------
    def create_tokens(self, data: dict) -> tuple[str, str]:
        """Genera un par access/refresh con validación de rol."""
        is_admin = data.get("rol") == "Admin"
        data["scope"] = self.roles_scope["Admin"] if is_admin else self.roles_scope["User"]

        access_exp = self.cfg.ACCESS_TOKEN_EXP_ADMIN if is_admin else self.cfg.ACCESS_TOKEN_EXP_MINUTES
        refresh_exp = self.cfg.REFRESH_TOKEN_EXP_ADMIN if is_admin else self.cfg.REFRESH_TOKEN_EXP_DAYS

        access_claims = self._build_payload(data, "access", int(access_exp))
        refresh_claims = self._build_payload(data, "refresh", int(refresh_exp))

        return (
            jwt.encode(access_claims, self.private_key, algorithm="RS256"),
            jwt.encode(refresh_claims, self.private_key, algorithm="RS256"),
        )

    def get_refresh_access_token(self, refresh_token: str) -> str:
        """Crea nuevo access token a partir de un refresh válido."""
        token_data = self.verify_token(refresh_token, expected_type="refresh")

        exp = int(self.cfg.ACCESS_TOKEN_EXP_ADMIN) if token_data.rol == "Admin" else int(self.cfg.ACCESS_TOKEN_EXP_MINUTES)

        payload = self._build_payload(
            {
                "username": token_data.sub,
                "rol": token_data.rol,
                "scope": token_data.scope,
                "device_id": token_data.device_id,
                "jti": token_data.jti,
            },
            "access",
            exp,
        )

        return jwt.encode(payload, self.private_key, algorithm="RS256")

   # -----------------------------
    # Token decoding & validation
    # -----------------------------
    def _decode_token(self, token: str, expected_type: str, issuer=None, audience=None) -> TokenModel:
        try:
            decoded = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                issuer=issuer or self.cfg.JWT_ISSUER,
                audience=audience or self.cfg.JWT_AUDIENCE,
            )

            # Validación semántica del contenido con Pydantic
            token_data = TokenModel(**decoded)

            if token_data.token_type != expected_type:
                raise AuthException(
                    f"Tipo de token incorrecto. Se esperaba '{expected_type}' y se recibió '{token_data.token_type}'.",
                    "InvalidTypeToken",
                    401,
                    "error",
                )

            return token_data

        except (ExpiredSignatureError, InvalidSignatureError, ImmatureSignatureError,
                DecodeError, InvalidAudienceError, InvalidIssuerError, InvalidTokenError) as e:
            raise AuthException(f"Error de token: {str(e)}", e.__class__.__name__, 401, "error")
        except Exception as e:
            raise AuthException(str(e), "TokenValidationError", 400, "error")

    def verify_token(self, token: str, expected_type: str = "access") -> TokenModel:
        """Verifica y retorna un TokenModel."""
        return self._decode_token(token, expected_type)
