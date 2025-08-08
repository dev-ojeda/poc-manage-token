# #!/usr/bin/env python
# # -*- coding: utf-8 -*-

# import uuid
# from datetime import datetime, timedelta, timezone
# from typing import Optional

# import bcrypt
# import jwt
# from app.config import Config
# from app.utils.db import Database
# from cryptography.hazmat.primitives import serialization
# from flask import Blueprint
# from icecream import ic
# from jwt.exceptions import (ExpiredSignatureError, InvalidAudienceError,
#                             InvalidIssuerError, InvalidTokenError)

# appManager_bp = Blueprint(
#     "appManager",
#     __name__,
# )
# class AppManager:
#     def __init__(self):
#         self.connexion = Database("blacklist.db")
#         self.private_key_path = Config.PATH_PRIVATE_KEY
#         self.public_key_path = Config.PATH_PUBLIC_KEY
#         self.private_key = self.load_private_key()
#         self.public_key = self.load_public_key()

#     def load_private_key(self):
#         try:
#             with open(self.private_key_path, "rb") as f:
#                 return serialization.load_pem_private_key(
#                     f.read(),
#                     password=None
#                 )
#         except FileNotFoundError:
#             ic("⚠️ Clave privada no encontrada")
#             return None

#     def load_public_key(self):
#         try:
#             with open(self.public_key_path, "r") as f:
#                 return serialization.load_pem_public_key(f.read().encode())
#         except FileNotFoundError:
#             ic("⚠️ Clave pública no encontrada")
#             return None

#     def validate_user(self, username: str, plain_password: str) -> Optional[dict]:
#         row = self.connexion.fetch_query("""
#             SELECT id, username, password, rol
#             FROM users
#             WHERE username = ?
#             LIMIT 1;
#         """, (username,))

#         if not row:
#             return None

#         user_id, user_name, hashed_password, rol = row[0]
#         ic(hashed_password)
#         if self.verify_password(plain_password, hashed_password):
#             return {
#                 "id": user_id,
#                 "username": user_name,
#                 "rol": rol
#             }
#         return None

#     def create_token(self, data: dict) -> tuple[str,str]:
#         access_payload = {
#             "sub": data.get("username"),   # <- clave
#             **data,
#             "jti": str(uuid.uuid4()),
#             "exp": datetime.now(timezone.utc) + timedelta(seconds=240),
#             "iat": datetime.now(timezone.utc),
#             "nbf": datetime.now(timezone.utc),
#             "iss": Config.JWT_ISSUER,
#             "aud": Config.JWT_AUDIENCE,
#             "type": "access"
#         }
#         refresh_payload = {
#             "sub": data.get("username"),   # <- clave
#             **data,
#             "jti": access_payload.get("jti"),
#             "exp": datetime.now(timezone.utc) + timedelta(seconds=360),
#             "iat": datetime.now(timezone.utc),
#             "nbf": datetime.now(timezone.utc),
#             "iss": Config.JWT_ISSUER,
#             "aud": Config.JWT_AUDIENCE,
#             "type": "refresh"
#         }
#         access_token  = jwt.encode(access_payload, self.private_key, algorithm="RS256")
#         refresh_token  = jwt.encode(refresh_payload, self.private_key, algorithm="RS256")
#         return access_token, refresh_token

#     def verify_token(self, token: str, expected_type: str = "access") -> Optional[dict]:
#         try:
#             decoded = jwt.decode(
#                 token,
#                 self.public_key,
#                 algorithms=["RS256"],
#                 issuer=Config.JWT_ISSUER,
#                 audience=Config.JWT_AUDIENCE
#             )

#             ic("🧩 Token decodificado OK", decoded)

#             # Validación de tipo
#             token_type = decoded.get("type")
#             if token_type != expected_type:
#                 ic(f"⛔ Tipo inválido: esperado={expected_type}, recibido={token_type}")
#                 return None

#             # Validación contra blacklist
#             jti = decoded.get("jti")
#             if not jti:
#                 ic("⚠️ Token sin JTI (ID único)")
#                 return None

#             if self.is_token_revoked(jti):
#                 ic("⛔ Token revocado en blacklist")
#                 return None

#             return decoded

#         except ExpiredSignatureError:
#             ic("⚠️ Token expirado.")
#         except InvalidAudienceError:
#             ic("⚠️ Audiencia inválida.")
#         except InvalidIssuerError:
#             ic("⚠️ Emisor inválido.")
#         except InvalidTokenError:
#             ic(f"⚠️ Token inválido.")
#         except Exception as e:
#             ic(f"🚨 Excepción inesperada al verificar token: {e}")

#         return None

#     def update_or_insert_refresh_token(self, username: str, device_id: str, refresh_token: str, user_agent=None, ip=None):
#         created_at = datetime.now(timezone.utc)
#         expires_at = (datetime.now(timezone.utc) + timedelta(seconds=360))
#         # Verifica si ya existe un token para ese device
#         existing = self.connexion.fetch_one("""
#             SELECT id FROM refresh_tokens
#             WHERE username = ? AND device_id = ?;
#         """, (username, device_id))

#         if existing:
#             # Actualiza token existente
#             return self.connexion.execute_query("""
#                 UPDATE refresh_tokens
#                 SET refresh_token = ?, created_at = ?, revoked_at = NULL
#                 WHERE username = ? AND device_id = ?;
#             """, (refresh_token, created_at, username, device_id))
#         else:
#             # Inserta nuevo token
#             return self.connexion.execute_query("""
#                 INSERT INTO refresh_tokens (
#                 username,
#                 device_id, 
#                 refresh_token, 
#                 created_at,
#                 expires_at,
#                 user_agent,
#                 ip_address)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#                 ON CONFLICT(username, device_id) DO UPDATE SET
#                 refresh_token = excluded.refresh_token,
#                 created_at = excluded.created_at,
#                 expires_at = excluded.expires_at,
#                 revoked_at = NULL,
#                 user_agent = excluded.user_agent,
#                 ip_address = excluded.ip_address;
#             """, (username, device_id, refresh_token, created_at, expires_at, user_agent, ip))

#     def update_store_refresh_token_revoked(self, refresh_token: str, device_id: str) -> None:
#         revoked_at = datetime.now(timezone.utc)
#         return self.connexion.execute_query("""
#             UPDATE refresh_tokens
#             SET revoked_at = ?
#             WHERE refresh_token = ? AND device_id = ?;
#         """, (revoked_at, refresh_token, device_id))

#     def is_valid_refresh_token(self, refresh_token: str, device_id: str):
#         revoked_at = self.connexion.fetch_one("""
#             SELECT revoked_at
#             FROM refresh_tokens
#             WHERE refresh_token = ? AND device_id = ?
#             AND expires_at > ?;
#         """, (refresh_token, device_id, datetime.now(timezone.utc).isoformat()))

#         return revoked_at  # puede ser None o un string/datetime

#     def is_token_revoked(self, jti: str) -> bool:
#         count = self.connexion.fetch_one("""
#             SELECT COUNT(*) FROM token_blacklist WHERE jti = ?
#         """, (jti,))
#         return count > 0

#     def revoke_token(self, jti:str) -> None:
#         return self.connexion.execute_query("""
#             INSERT OR IGNORE INTO token_blacklist (jti) VALUES (?)
#         """,(jti,))

#     def hash_password(self,plain_password):
#         return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

#     def verify_password(self, plain_password, hashed_password):
#         return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))