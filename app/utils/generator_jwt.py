from icecream import ic
import jwt
import datetime
from datetime import timezone, timedelta
from cryptography.hazmat.primitives import serialization

from app.auth import AuthException
from app.config import Config
# 🔑 Clave secreta (puede ser una env var)
def load_key(path, is_private=False):
    try:
        with open(path, "r") as f:
            content = f.read().encode()
            return serialization.load_pem_private_key(content, password=None) if is_private else serialization.load_pem_public_key(content)
    except FileNotFoundError:
        ic(f"⚠️ Clave {'privada' if is_private else 'pública'} no encontrada en {path}")
        return None
private_key = load_key(Config.PATH_PRIVATE_KEY, is_private=True)
public_key = load_key(Config.PATH_PUBLIC_KEY, is_private=False)

def _build_payload(token_type: str, valid_seconds: float, exp_minutes: float ) -> dict:
    now = datetime.datetime.now(tz=timezone.utc)
    return {
        "iat": now.timestamp(),
        "nbf": now.timestamp(),
        "exp": int(((now + timedelta(minutes=exp_minutes)).timestamp()) * 1000),
        "sub": "usuario123",             # subject (ej: user_id)
        "role": "admin",
        "type": token_type
    }


def generar_jwt() -> tuple[str, str]:
   
    payload_access = _build_payload(token_type="access", valid_seconds=30, exp_minutes=2)
    payload_refresh = _build_payload(token_type="refresh", valid_seconds=30, exp_minutes=4)

    return (
            jwt.encode(payload_access, private_key, algorithm="RS256"),
            jwt.encode(payload_refresh, private_key, algorithm="RS256")
        )


def verificar_jwt(token: str, expected_type: str) -> dict:
    try:
        decoded = jwt.decode(token, public_key, algorithms=["RS256"])
        if decoded["type"] != expected_type:
            raise AuthException(
                    f"Tipo de token inválido. Se esperaba '{expected_type}', se recibió '{decoded.get('type')}'",
                    "InvalidTypeToken",
                    401,
                    "error"
                )
        return decoded
    except jwt.ExpiredSignatureError:
        return {"error": "❌ Token expirado"}
    except jwt.ImmatureSignatureError:
        return {"error": "⏳ Token aún no es válido (nbf)"}
    except jwt.InvalidTokenError as e:
        return {"error": f"⚠️ Token inválido: {str(e)}"}
    except Exception as e:
        return {"error": f"⚠️ Exception: {str(e)}"}

# ----------------- Uso -----------------

data = {
}


access_token, refresh_token = generar_jwt()
ic("🔐 ACCESS_TOKEN JWT:", access_token)
ic("🔐 REFRESH_TOKEN JWT:", refresh_token)

validar_access = verificar_jwt(token=access_token,expected_type="access")
validar_refresh = verificar_jwt(token=refresh_token,expected_type="refresh")
ic("✅ Verificación:", validar_access)
ic("✅ Verificación:", validar_refresh)

