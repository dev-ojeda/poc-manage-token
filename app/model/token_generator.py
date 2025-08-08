import uuid
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidTokenError,
    InvalidSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
)
from icecream import ic

from app.config import Config
from auth.exceptions.auth_exceptions import AuthException

class TokenGenerator:
    def __init__(self):
        self.access_exp = int(Config.ACCESS_TOKEN_EXP_SECONDS)
        self.access_exp_admin = int(Config.ACCESS_TOKEN_EXP_ADMIN)
        self.refresh_exp = int(Config.REFRESH_TOKEN_EXP_SECONDS)
        self.refresh_exp_admin = int(Config.REFRESH_TOKEN_EXP_ADMIN)
        self.access_exp_global = int(Config.ACCESS_TOKEN_GLOBAL_EXP_SECONDS)
        self.valid_roles = Config.VALID_ROLES
        self.roles_scope = Config.ROLE_SCOPES
        self.private_key = self._load_key(Config.PATH_PRIVATE_KEY, is_private=True)
        self.public_key = self._load_key(Config.PATH_PUBLIC_KEY, is_private=False)

    def _load_key(self, path, is_private=False):
        try:
            with open(path, "r") as f:
                content = f.read().encode()
                return serialization.load_pem_private_key(content, password=None) if is_private else serialization.load_pem_public_key(content)
        except FileNotFoundError:
            ic(f"⚠️ Clave {'privada' if is_private else 'pública'} no encontrada en {path}")
            return None

    def _current_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def _is_valid_role(self, role) -> bool:
        return role in self.valid_roles

    def _build_payload(self, data: dict, token_type: str, exp_seconds: int) -> dict:
        now = self._current_utc()
        data["jti"] = str(data.get("jti") or uuid.uuid4())
        return {
            "sub": data.get("username", "anonymous"),
            **data,
            "jti": data["jti"],
            "rol": data.get("rol"),
            "scope": data.get("scope", "default"),
            "exp": now + timedelta(seconds=exp_seconds),
            "iat": now,
            "nbf": now,
            "iss": Config.JWT_ISSUER,
            "aud": Config.JWT_AUDIENCE,
            "type": token_type
        }

    def _build_global_payload(self, token_type: str, exp_minutes: int) -> dict:
        now = self._current_utc()
        return {
            "sub": "admin@example.com",
            "rol": "Admin",
            "scope": "full_control",
            "iat": int(now.timestamp()),
            "nbf": now,
            "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
            "iss": "flask-root",
            "type": token_type
        }

    def create_tokens(self, data: dict) -> tuple[str, str]:

        if data.get("rol") == "Admin":
            payload_access = self._build_payload(data, "access", self.access_exp_admin)
            payload_refresh = self._build_payload(data, "refresh", self.refresh_exp_admin)
        else:
            payload_access = self._build_payload(data, "access", self.access_exp)
            payload_refresh = self._build_payload(data, "refresh", self.refresh_exp)
        

        return (
            jwt.encode(payload_access, self.private_key, algorithm="RS256"),
            jwt.encode(payload_refresh, self.private_key, algorithm="RS256")
        )

    def create_tokens_global(self) -> str:
        payload = self._build_global_payload("access", self.access_exp_global)
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _decode(self, token: str, expected_type: str = "access", issuer=None, audience=None) -> dict:
        try:
            decoded = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                issuer=issuer or Config.JWT_ISSUER,
                audience=audience or Config.JWT_AUDIENCE
            )

            if decoded.get("type") != expected_type:
                raise AuthException(
                    f"Tipo de token inválido. Se esperaba '{expected_type}', se recibió '{decoded.get('type')}'", 
                    "InvalidTokenError", 
                    401
                )
                # raise InvalidTokenError(f"Tipo de token inválido. Se esperaba '{expected_type}', se recibió '{decoded.get('type')}'")

            return decoded

        except ExpiredSignatureError:
            raise AuthException(
                "Tu sesión ha expirado. Por favor inicia sesión nuevamente.", 
                "ExpiredSignatureError", 
                401
            )
            # return {"error": "Tu sesión ha expirado. Por favor inicia sesión nuevamente.", "code": "ExpiredSignatureError"}, 401

        except InvalidSignatureError:
            raise AuthException(
                "Firma invalida.", 
                "InvalidSignatureError", 
                401
            )
            # return {"error": "Firma invalida.", "code": "InvalidSignatureError"}, 401

        except DecodeError:
            raise AuthException(
                "Acceso no autorizado (token mal decodificado).", 
                "DecodeError", 
                400
            )
            # return {"error": "Acceso no autorizado (token mal decodificado).", "code": "DecodeError"}, 400

        except InvalidAudienceError:
            raise AuthException(
                "Acceso no autorizado (audiencia inválida).", 
                "InvalidAudienceError", 
                403
            )
            # return {"error": "Acceso no autorizado (audiencia inválida).", "code": "InvalidAudienceError"}, 403

        except InvalidIssuerError:
             raise AuthException(
                "Acceso no autorizado (emisor del token no válido).", 
                "InvalidIssuerError", 
                403
            )
            # return {"error": "Acceso no autorizado (emisor del token no válido).", "code": "InvalidIssuerError"}, 403

        except InvalidTokenError:
            raise AuthException(
                "Token no válido. Por favor vuelve a iniciar sesión.", 
                "InvalidTokenError", 
                401
            )
            # return {"error": "Token no válido. Por favor vuelve a iniciar sesión.", "code": "InvalidTokenError"}, 401

        except Exception as e:
            return {"error": f"Error inesperado: {str(e)}"}, 500


    def _decode_global(self, token: str, expected_type: str = "access", issuer=None, audience=None) -> dict:
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
                    "InvalidTokenError", 
                    401
                )
                # raise InvalidTokenError(f"Tipo de token inválido. Se esperaba '{expected_type}', se recibió '{decoded.get('type')}'")

            return decoded

        except ExpiredSignatureError:
            raise AuthException(
                "Tu sesión ha expirado. Por favor inicia sesión nuevamente.", 
                "ExpiredSignatureError", 
                401
            )
            # return {"error": "Tu sesión ha expirado. Por favor inicia sesión nuevamente.", "code": "ExpiredSignatureError"}, 401

        except InvalidSignatureError:
            raise AuthException(
                "Firma invalida.", 
                "InvalidSignatureError", 
                401
            )
            # return {"error": "Firma invalida.", "code": "InvalidSignatureError"}, 401

        except DecodeError:
            raise AuthException(
                "Acceso no autorizado (token mal decodificado).", 
                "DecodeError", 
                400
            )
            # return {"error": "Acceso no autorizado (token mal decodificado).", "code": "DecodeError"}, 400

        except InvalidAudienceError:
            raise AuthException(
                "Acceso no autorizado (audiencia inválida).", 
                "InvalidAudienceError", 
                403
            )
            # return {"error": "Acceso no autorizado (audiencia inválida).", "code": "InvalidAudienceError"}, 403

        except InvalidIssuerError:
             raise AuthException(
                "Acceso no autorizado (emisor del token no válido).", 
                "InvalidIssuerError", 
                403
            )
            # return {"error": "Acceso no autorizado (emisor del token no válido).", "code": "InvalidIssuerError"}, 403

        except InvalidTokenError:
            raise AuthException(
                "Token no válido. Por favor vuelve a iniciar sesión.", 
                "InvalidTokenError", 
                401
            )
            # return {"error": "Token no válido. Por favor vuelve a iniciar sesión.", "code": "InvalidTokenError"}, 401

        except Exception as e:
            return {"error": f"Error inesperado: {str(e)}"}, 500
    def verify_token(self, token: str, expected_type: str = "access") -> dict:
        return self._decode(token, expected_type)

    def verify_token_global(self, token: str, expected_type: str = "access") -> dict:
        return self._decode_global(token=token, expected_type=expected_type, issuer="flask-root")

    def get_role_from_token(self, token: str) -> str:
        try:
            decoded = self.verify_token(token)
            return decoded.get("rol", "User")
        except Exception as e:
            ic(f"Error al obtener rol desde token: {e}")
            return "User"