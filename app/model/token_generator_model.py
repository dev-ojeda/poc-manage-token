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
from icecream import ic

from app.config import Config
from app.auth.exceptions.auth_exceptions import AuthException

class TokenGeneratorModel:
    def __init__(self):
        self.access_exp = int(Config.ACCESS_TOKEN_EXP_MINUTES)
        self.access_exp_admin = int(Config.ACCESS_TOKEN_EXP_ADMIN)
        self.refresh_exp = int(Config.REFRESH_TOKEN_EXP_DAYS)
        self.refresh_exp_admin = int(Config.REFRESH_TOKEN_EXP_ADMIN)
        self.access_exp_global = int(Config.ACCESS_TOKEN_GLOBAL_EXP_SECONDS)
        self.valid_roles = Config.VALID_ROLES
        self.roles_scope = Config.ROLE_SCOPES
        self.jwt_issuer = Config.JWT_ISSUER
        self.jwt_audience = Config.JWT_AUDIENCE
        self.private_key = self._load_key(Config.PATH_PRIVATE_KEY, is_private=True)
        self.public_key = self._load_key(Config.PATH_PUBLIC_KEY, is_private=False)

    def _load_key(self, path, is_private=False):
        try:
            with open(path, "rb") as f:
                content = f.read()
                return serialization.load_pem_private_key(content, password=None) if is_private else serialization.load_pem_public_key(content)
        except FileNotFoundError:
            ic(f"⚠️ Clave {'privada' if is_private else 'pública'} no encontrada en {path}")
            return None

    def _is_valid_role(self, role) -> bool:
        return role in self.valid_roles

    def _build_payload(self, data: dict, token_type: str, exp_delta: int) -> dict:
        # Fecha/hora actual en UTC
        now_utc = datetime.datetime.now(tz=timezone.utc)
        if token_type == "refresh":
            exp_ts = now_utc + timedelta(days=exp_delta)
        else:
            exp_ts = now_utc + timedelta(minutes=exp_delta)
        return {
            "sub": data["username"],
            **data,
            "rol": data["rol"],
            "scope": data["scope"],
            "iat": now_utc.timestamp(),
            "nbf": now_utc.timestamp(),
            "exp": int(exp_ts.timestamp()),
            "iss": self.jwt_issuer,
            "aud": self.jwt_audience,
            "type": token_type
        }

    def _build_global_payload(self, token_type: str, exp_minutes: int) -> dict:
        # Fecha/hora actual en UTC
        now_utc = datetime.datetime.now(tz=timezone.utc)
        exp_ts = now_utc + timedelta(minutes=exp_minutes)
        return {
            "sub": "admin@example.com",
            "rol": "Admin",
            "scope": "full_control",
            "iat": now_utc.timestamp(),
            "nbf": now_utc.timestamp(),
            "exp": int(exp_ts.timestamp()),
            "iss": "flask-root",
            "type": token_type,
            "jti": str(uuid.uuid4())
        }

    def create_tokens(self, data: dict) -> tuple[str, str]:
        """
        Genera access_token y refresh_token con el mismo jti
        """
        if data["rol"] == "Admin":
            data["scope"] = self.roles_scope["Admin"]
            payload_access = self._build_payload(data=data, token_type="access", exp_delta=self.access_exp_admin)
            payload_refresh = self._build_payload(data=data, token_type="refresh", exp_delta=self.refresh_exp_admin)
        else:
            data["scope"] = self.roles_scope["User"]
            payload_access = self._build_payload(data=data , token_type="access", exp_delta=self.access_exp)
            payload_refresh = self._build_payload(data=data, token_type="refresh", exp_delta=self.refresh_exp)


        return (
            jwt.encode(payload_access, self.private_key, algorithm="RS256"),
            jwt.encode(payload_refresh, self.private_key, algorithm="RS256")
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Recibe un refresh_token válido y devuelve un nuevo access_token
        con el mismo jti.
        """
        decoded = self._decode(refresh_token, expected_type="refresh")

        data = {
            "username": decoded["sub"],
            "rol": decoded["rol"],
            "scope": decoded["scope"],
            "jti": decoded["jti"],   # reutilizamos mismo jti
        }

        exp_seconds = (
            self.access_exp_admin if data["rol"] == "Admin" else self.access_exp
        )

        payload_access = self._build_payload(data, "access", exp_seconds)

        return jwt.encode(payload_access, self.private_key, algorithm="RS256")

    def create_tokens_global(self) -> str:
        payload = self._build_global_payload("access", self.access_exp_global)
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _decode(self, token: str, expected_type: str = "access") -> dict:
      
        try:
            decoded = jwt.decode(
                token, 
                self.public_key,
                algorithms=["RS256"],
                issuer=self.jwt_issuer,
                audience=self.jwt_audience
            )

            if decoded.get("type") != expected_type:
                raise AuthException(
                    f"Tipo de token inválido. Se esperaba '{expected_type}', se recibió '{decoded.get('type')}'",
                    "InvalidTypeToken",
                    401
                )

            return decoded

        except ExpiredSignatureError:
            raise AuthException("Tu sesión ha expirado. Por favor inicia sesión nuevamente.", "ExpiredSignatureError", 401, "error")
        except InvalidSignatureError:
            raise AuthException("Firma inválida.", "InvalidSignatureError", 401, "error")
        except ImmatureSignatureError:
            raise AuthException("Token aún no es válido (nbf).", "ImmatureSignatureError", 400, "error")
        except DecodeError:
            raise AuthException("Acceso no autorizado (token mal decodificado).", "DecodeError", 400, "error")
        except InvalidAudienceError:
            raise AuthException("Acceso no autorizado (audiencia inválida).", "InvalidAudienceError", 403, "error")
        except InvalidIssuerError:
            raise AuthException("Acceso no autorizado (emisor del token no válido).", "InvalidIssuerError", 403, "error")
        except InvalidTokenError:
            raise AuthException("Token no válido. Por favor vuelve a iniciar sesión.", "InvalidTokenError", 401, "error")

    def _decode_global(self, token: str, expected_type: str = "access", issuer=None) -> dict:
        try:
            decoded = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                issuer=issuer or Config.JWT_ISSUER
            )

            if decoded.get("type") != expected_type:
                raise AuthException(
                    f"Tipo de token inválido. Se esperaba '{expected_type}', se recibió '{decoded.get('type')}'",
                    "InvalidTypeToken",
                    401,
                    "error"
                )

            return decoded

        except ExpiredSignatureError:
            raise AuthException("Tu sesión ha expirado. Por favor inicia sesión nuevamente.", "ExpiredSignatureError", 401, "error")

        except InvalidSignatureError:
            raise AuthException("Firma inválida.", "InvalidSignatureError", 401, "error")

        except DecodeError:
            raise AuthException("Acceso no autorizado (token mal decodificado).", "DecodeError", 400, "error")

        except InvalidAudienceError:
            raise AuthException("Acceso no autorizado (audiencia inválida).", "InvalidAudienceError", 403, "error")

        except InvalidIssuerError:
            raise AuthException("Acceso no autorizado (emisor del token no válido).", "InvalidIssuerError", 403, "error")

        except InvalidTokenError:
            raise AuthException("Token no válido. Por favor vuelve a iniciar sesión.", "InvalidTokenError", 401, "error")

        except Exception as e:
            raise AuthException(f"Error inesperado: {str(e)}", "UnexpectedError", 500)
   
    
    def verify_token(self, token: str, expected_type: str = "access") -> dict:
        return self._decode(token=token , expected_type=expected_type)

    def verify_token_global(self, token: str, expected_type: str = "access") -> dict:
        return self._decode_global(token=token, expected_type=expected_type, issuer="flask-root")

    def get_role_from_token(self, token: str) -> str:
        try:
            decoded = self.verify_token(token)
            return decoded.get("rol", "User")
        except Exception as e:
            ic(f"Error al obtener rol desde token: {e}")
            return "User"