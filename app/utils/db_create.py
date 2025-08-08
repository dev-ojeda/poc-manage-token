# from pymongo import DESCENDING, MongoClient, ASCENDING, errors
from app.config import Config
from pymongo import ASCENDING, DESCENDING, errors
from pymongo.mongo_client import MongoClient, OperationFailure
from pymongo.server_api import ServerApi
from datetime import datetime, timezone
from icecream import ic

# client = MongoClient("mongodb://localhost:27017/")
client = MongoClient(Config.MONGO_URI_CLUSTER_X509, tls=True, tlsCertificateKeyFile=Config.MONGODB_X509, server_api=ServerApi('1'))
db = client[Config.MONGO_DB]


def db_create_collection():
    # 1. Crear colección con validación opcional
    try:
        # Crear colección (si no existe)
        if "refresh_tokens" not in db.list_collection_names():
           # 1. Crear colección con validador jsonSchema
            try:
                db.create_collection("refresh_tokens", validator={
                            "$jsonSchema": {
                            "bsonType": "object",
                            "required": ["username", "device_id", "jti", "refresh_token", "created_at", "expires_at"],
                            "properties": {
                                "username":     {"bsonType": "string","description": "Debe ser una cadena de texto"},
                                "device_id":    {"bsonType": "string","description": "Identificador único del dispositivo"},
                                "jti":          {"bsonType": "string","description": "Token ID (único por refresh)"},
                                "refresh_token":{"bsonType": "string","description": "Token refresh JWT"},
                                "created_at":   {"bsonType": "date","description": "Fecha de creación del token"},
                                "update_at":    {"bsonType": ["date", "null"],"description": "Fecha de actualización del token"},
                                "expires_at":   {"bsonType": "date","description": "Fecha de expiración"},
                                "revoked_at":   {"bsonType": ["date", "null"],"description": "Si fue revocado, fecha de revocación"},
                                "used_at":      {"bsonType": ["date", "null"],"description": "Fecha en la que se usó el token (null si no usado)"}, 
                                "refresh_attempts": {"bsonType": "int","minimum": 0,"maximum": 3,"description": "Intentos de refresco de sesión"}, 
                                "browser":   {"bsonType": ["string", "null"],"description": "Navegador extraído del User-Agent"},
                                "os":   {"bsonType": ["string", "null"],"description": "Sistema operativo extraído del User-Agent"},
                                "user_agent":   {"bsonType": ["string", "null"],"description": "User-Agent del navegador"},
                                "ip_address":   {"bsonType": ["string", "null"],"description": "IP del dispositivo"}
                            }
                        }
                    },
                    validationLevel="strict",
                    validationAction="error"
                )
                ic("Colección 'refresh_tokens' creada correctamente")
            except errors.CollectionInvalid:
                ic("La colección ya existe, continuando con los índices...")
            # 2. Crear índices para máxima eficiencia
            try:
                # Previene duplicados: solo un refresh_token activo por device + user
                db.refresh_tokens.create_index(
                    [("username", ASCENDING), ("device_id", ASCENDING)],
                    unique=True,
                    name="idx_device_user"
                )

                # Búsquedas de refresh_token válidos (por device y no expirados)
                db.refresh_tokens.create_index(
                    [("refresh_token", ASCENDING), ("device_id", ASCENDING), ("expires_at", ASCENDING)],
                    name="idx_refresh_token_device_expiry"
                )

                db.refresh_tokens.create_index(
                    [("username", ASCENDING), ("update_at", ASCENDING), ("expires_at", ASCENDING)],
                    name="idx_username_update_expires_at"
                )

                # Eliminación automática de tokens expirados
                db.refresh_tokens.create_index(
                    [("expires_at", ASCENDING)],
                    expireAfterSeconds=0,
                    name="idx_ttl_expired_refresh_tokens"
                )
                db.refresh_tokens.create_index(
                    [("username", ASCENDING)],
                    name="idx_user_sessions"
                )
                ic("Índices creados con éxito")
            except OperationFailure as e:
                ic(f"Error creando índice: {e}")
  
        elif "session_audit" not in db.list_collection_names():
            try:
                db.create_collection("session_audit", validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["session_id", "user_id", "event_type", "old_value", "new_value", "timestamp"],
                        "properties": {
                            "session_id": { "bsonType": "string" },
                            "user_id": { "bsonType": "string" },
                            "event_type": {
                                "enum": ["ip_change", "user_agent_change", "revoked"]
                            },
                            "old_value": { "bsonType": "string" },
                            "new_value": { "bsonType": "string" },
                            "ip_address": { "bsonType": "string" },
                            "user_agent": { "bsonType": "string" },
                            "timestamp": { "bsonType": "date" }
                        }
                    }
                },
                validationLevel="strict",
                validationAction="error"
              )
            except errors.CollectionInvalid as e:
                ic("La colección ya existe, continuando con los índices...")
            try:
                db.session_audit.create_index(
                    [("session_id", ASCENDING), ("device_id", ASCENDING), ("timestamp", DESCENDING)],
                    name="idx_session_device_id_timestamp"
                )
                db.session_audit.create_index(
                    [("user_id", ASCENDING)],
                    name="idx_user_id"
                )
                db.session_audit.create_index(
                    [("session_id", ASCENDING)],
                    name="idx_session_id"
                )
                db.session_audit.create_index(
                    [("event_type", ASCENDING)],
                    name="idx_event_type"
                )
                db.session_audit.create_index(
                    [("timestamp", ASCENDING)],
                    name="idx_timestamp"
                )
            except errors.OperationFailure as e:
                ic(f"Error creando índice: {e}")
        elif "active_sessions" not in db.list_collection_names():
            try:
               db.create_collection("active_sessions", validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "device_id", "ip_address", "browser", "os", "login_at", "refresh_token", "is_revoked", "status"],
                        "properties": {
                            "user_id": {
                            "bsonType": "objectId",
                            "description": "ID del usuario relacionado a la sesión"
                            },
                            "device_id": {
                            "bsonType": "string",
                            "description": "Identificador único del dispositivo"
                            },
                            "ip_address": {
                            "bsonType": "string",
                            "description": "Dirección IP del cliente"
                            },
                            "browser": {"bsonType": ["string", "null"],"description": "Navegador extraído del User-Agent"},
                            "os":   {"bsonType": ["string", "null"],"description": "Sistema operativo extraído del User-Agent"},
                            "login_at": {
                            "bsonType": "date",
                            "description": "Fecha/hora del inicio de sesión"
                            },
                            "last_refresh_at": {
                            "bsonType": ["date", "null"],
                            "description": "Fecha del último refresh token, si existe"
                            },
                            "refresh_token": {
                            "bsonType": "string",
                            "description": "Token de actualización asociado a la sesión"
                            },
                            "is_revoked": {
                            "bsonType": "bool",
                            "description": "Indica si la sesión ha sido revocada manualmente o por seguridad"
                            },
                            "revoked_at": {
                            "bsonType": ["date", "null"],
                            "description": "Fecha de revocación (si aplica)"
                            },
                            "reason": {
                            "bsonType": ["string", "null"],
                            "description": "Razón de la revocación (expulsión, expiración, múltiples intentos, etc.)"
                            },
                            "status": {
                            "bsonType": "string",
                            "enum": ["active", "revoked", "expired"],
                            "description": "Estado lógico de la sesión"
                            },
                            "role": {
                            "bsonType": ["string", "null"],
                            "description": "Rol del usuario al momento de iniciar sesión"
                            }
                        }
                    }
                },
                validationLevel="strict",
                validationAction="error"
            )
            except errors.CollectionInvalid as e:
                ic("La colección ya existe, continuando con los índices...")
            try:
                # Índices sugeridos
                # 🔍 Búsqueda rápida por usuario
                db.active_sessions.create_index([("user_id", ASCENDING)], name="idx_user_id");

                 # 🔍 Consultas por dispositivo + usuario
                db.active_sessions.create_index([("user_id", ASCENDING), ("device_id", ASCENDING)], name="idx_user_device_id");

                 # ⚠️ Buscar sesiones activas rápido
                db.active_sessions.create_index([("status", ASCENDING), ("is_revoked", ASCENDING)], name="idx_status_revoked");

                 # 📅 Orden por fecha de login (útil para paneles)
                db.active_sessions.create_index([("login_at", DESCENDING)], name="idx_login_at");

                 # 🔐 Índice para revocar tokens por refresh_token
                db.active_sessions.create_index([("refresh_token", ASCENDING)], unique=True, name="idx_refresh_token");

                 # ⚙️ Índice compuesto para filtros complejos (opcional)
                db.active_sessions.create_index([("user_id", ASCENDING), ("status", ASCENDING), ("is_revoked", ASCENDING)], name="idx_user_id_status_revoked");
                # db.active_sessions.create_index("user_id", name="idx_user_id")
                # db.active_sessions.create_index("device_id", name="idx_device_id")
                # db.active_sessions.create_index("refresh_token", unique=True, name="idx_refresh_token")
                # db.active_sessions.create_index([("status", ASCENDING), ("is_revoked", ASCENDING)], name="idx_status_revoked")
            except errors.OperationFailure as e:
                ic(f"Error creando índice: {e}")
        elif "users" not in db.list_collection_names():
            db.create_collection("users", validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["username", "password", "rol", "created_at", "updated_at"],
                    "properties": {
                        "username": {
                            "bsonType": "string",
                            "description": "Debe ser una cadena y es obligatoria"
                        },
                        "password": {
                            "bsonType": "string",
                            "description": "Contraseña obligatoria"
                        },
                        "email": {
                          "bsonType": ["string", "null"],
                          "pattern": "^[^@]+@[^@]+\\.[^@]+$",
                          "description": "Email válido opcional"
                        },
                        "rol": {
                            "enum": ["User", "Admin"],
                            "description": "Solo puede ser 'User' o 'Admin'"
                        },
                        "created_at": {
                            "bsonType": "date",
                            "description": "Fecha de creación"
                        },
                        "updated_at": {
                            "bsonType": "date",
                            "description": "Fecha de actualizacion"
                        },
                        "failed_attempts": {
                          "bsonType": "int",
                          "minimum": 0,
                          "description": "Intentos fallidos, debe ser >= 0"
                        },
                         "blocked_until": {
                            "bsonType": ["date", "null"],
                            "description": "Verificar Bloqueo"
                        }
                    }
                }
                },
                validationLevel="strict",
                validationAction="error"
            )
               # Crear índices únicos para username y email
            try:
                db.users.create_index("username", unique=True, name="idx_unique_username")
                db.users.create_index([("email", ASCENDING)], unique=True, sparse=True, name="idx_unique_email")  # sparse permite nulos
                db.users.create_index([("rol", ASCENDING)], name="idx_rol")
                db.users.create_index([("blocked_until", ASCENDING)], name="idx_blocked_until")
            except errors.OperationFailure as e:
                ic(f"Error creando índice: {e}")
            ic("Colección 'users' creada con validación de esquema")
        elif "token_blacklist" not in db.list_collection_names():
            db.create_collection(
                "token_blacklist",
                validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["token", "revoked_at"],
                        "properties": {
                            "token": {"bsonType": "string"},
                            "revoked_at": {"bsonType": "date"},
                            "device_id": {"bsonType": ["string", "null"]},
                            "username": {"bsonType": ["string", "null"]},
                            "reason": {"bsonType": ["string", "null"]}
                        }
                    }
                },
                validationLevel="strict",
                validationAction="error"
            )
            try:
                db.token_blacklist.create_index(
                    [("token", ASCENDING)],
                    unique=True,
                    name="idx_unique_token"
                )
                ic("Índice único 'jti' creado con sparse=True")
            except errors.OperationFailure as e:
                ic(f"Error creando índice: {e}")
            ic("Colección 'token_blacklist' creada")
        elif "global_tokens" not in db.list_collection_names():
            db.create_collection("global_tokens", validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["token", "created_at", "expires_at"],
                        "properties": {
                            "token": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "expires_at": {"bsonType": "date"},
                            "ip_address": {"bsonType": ["string", "null"]},
                            "user_agent": {"bsonType": ["string", "null"]}
                        }
                    }
                },
                validationLevel="strict",
                validationAction="error"
            )
            ic("Colección 'global_tokens' creada")
    except errors.CollectionInvalid as e:
        ic(f"La colección ya existe -> {e}")

def db_create_user():
    db.users.insert_one({
    "username": "admin@example.com",
    "password": "$2b$12$xOjASwdN4rZxUgztrC.WPO1UeLDt4mmM0NWZUH8k7ZyaHl8PUVxi6",
    "email": "admin@example.com",
    "rol": "Admin",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "failed_attempts": 0,
    "blocked_until": None
})
#     db.users.insert_one({
#     "username": "user@example.com",
#     "password": "$2b$12$xOjASwdN4rZxUgztrC.WPO1UeLDt4mmM0NWZUH8k7ZyaHl8PUVxi6",
#     "email": "user@example.com",
#     "rol": "User",
#     "created_at": datetime.now(timezone.utc),
#     "updated_at": datetime.now(timezone.utc),
#     "failed_attempts": 0,
#     "blocked_until": None
# })
#     db.users.insert_one({
#     "username": "user1@example.com",
#     "password": "$2b$12$xOjASwdN4rZxUgztrC.WPO1UeLDt4mmM0NWZUH8k7ZyaHl8PUVxi6",
#     "email": "user1@example.com",
#     "rol": "User",
#     "created_at": datetime.now(timezone.utc),
#     "updated_at": datetime.now(timezone.utc),
#     "failed_attempts": 0,
#     "blocked_until": None
# })

def main():
    # db_create_user()
    db_create_collection()

if __name__ == "__main__":
    main()


