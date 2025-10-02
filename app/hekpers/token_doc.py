from typing import TypedDict

class TokenDoc(TypedDict, total=False):
    sub: str
    iat: float
    nbf: float
    exp: int
    iss: str
    aud: str
    token_type: str
    jti: str
    rol: str
    scope: str
    device_id: str
