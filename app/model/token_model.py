from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Optional


class TokenModel(BaseModel):
    sub: str
    iat: float
    nbf: float
    exp: int
    iss: str
    aud: Optional[str] = None
    token_type: str
    jti: str
    rol: str
    scope: str
    device_id: Optional[str] = None

    @validator("exp", pre=True)
    def validate_exp(cls, v):
        if not v:
            raise ValueError("Campo exp ausente o inválido")
        if datetime.now().timestamp() > v:
            raise ValueError("Token expirado")
        return v

    @validator("token_type")
    def check_type(cls, v):
        if v not in ("access", "refresh"):
            raise ValueError("token_type inválido")
        return v
