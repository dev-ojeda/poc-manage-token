#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime 
from datetime import timedelta, timezone
import json
import random
import time
import uuid

from bson import ObjectId
from pymongo.cursor import SON
from app.config import Config
from pymongo import ASCENDING, DESCENDING, errors
from pymongo.mongo_client import MongoClient, OperationFailure
from pymongo.server_api import ServerApi
from icecream import ic
from faker import Faker

from app.dao.metrics_dao import MetricsDAO
from app.model.metrics_model import MetricModel
# client = MongoClient("mongodb://localhost:27017/")
client = MongoClient(
    Config.MONGO_URI_CLUSTER_X509, 
    tls=True, 
    tlsCertificateKeyFile=Config.MONGODB_X509, 
    server_api=ServerApi('1'),
    tz_aware=True, 
    tzinfo=timezone.utc,
    maxPoolSize=100,
    serverSelectionTimeoutMS=3000
)
db = client[Config.MONGO_DB]
col_metrics_api = db["performance_metrics_api"]
col_metrics = db["metrics"]
faker = Faker()
# Eventos disponibles
event_types = [
    "ip_change", 
    "user_agent_change", 
    "revoked",
    "login", 
    "logout", 
    "refresh_token", 
    "close", 
    "session_update", 
    "multiple_attempts", 
    "expiration"
]
# Posibles IPs base
ips = ["192.168.1.", "10.0.0.", "172.16.0."]

# Posibles User Agents
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (Linux; Android 11)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2)",
    "PostmanRuntime/7.31.3"
]
# UserId de prueba
user_id = "68734c48ee99af408e0781a0"
user_oid = ObjectId(user_id)
# Configuración
reasons = [
    "ip_change",
    "user_agent_change",
    "revoked",
    "multiple_attempts",
    "logout",
    "expiration",
    "login",
    "refresh_token",
    "close"
],
statuses = ["active", "revoked", "expired"]
base_date = datetime.datetime(2025, 8, 1, 12, 0, 0)
# Datos base del JSON proporcionado
base_user = {
    "_id": {"$oid": "68734c48ee99af408e0781a0"},
    "username": "user@example.com",
    "password": "$2b$12$xOjASwdN4rZxUgztrC.WPO1UeLDt4mmM0NWZUH8k7ZyaHl8PUVxi6",
    "email": "user@example.com",
    "rol": "User",
    "created_at": {"$date": "2025-07-13T06:03:50.279Z"},
    "updated_at": {"$date": "2025-07-13T06:03:50.848Z"},
    "failed_attempts": 0,
    "blocked_until": None
}
# Configuración de prueba
pages = ["/profile", "/dashboard", "/login", "/signup"]
urls = pages
roles = ["user", "admin"]
browsers = ["Chrome", "Firefox", "Edge", "Safari"]
oses = ["Windows", "MacOS", "Linux"]
categories = ["apiresponsetime", "webvitals"]
metric_names = {
    "apiresponsetime": ["GET /api/profile", "POST /api/login", "GET /api/dashboard"],
    "webvitals": ["LCP", "FID", "CLS", "INP", "TTFB"]
}
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
                        "required": ["session_id", "user_id", "event_type", "timestamp"],
                        "properties": {
                            "session_id": { "bsonType": "string" },
                            "user_id": { "bsonType": "string" },
                            "event_type": {
                                "enum": [
                                    "ip_change", 
                                    "user_agent_change", 
                                    "revoked",
                                    "login", 
                                    "logout", 
                                    "refresh_token", 
                                    "close", 
                                    "session_update"
                                ]
                            },
                            "old_value": { "bsonType": ["string", "null"] },
                            "new_value": { "bsonType": ["string", "null"] },
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
                ic(f"La colección ya existe, continuando con los índices... {e}")
            try:
                db.session_audit.create_index(
                    [("user_id", ASCENDING), ("event_type", ASCENDING), ("timestamp", DESCENDING)],
                    name="idx_user_event_time"
                )
                db.session_audit.create_index(
                    [("event_type", ASCENDING), ("timestamp", DESCENDING)],
                    name="idx_event_time"
                )
                db.session_audit.create_index(
                    [("timestamp", DESCENDING)],
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
                                "bsonType": "string",
                                "enum": ["ip_change", "user_agent_change", "revoked", "multiple_attempts", "logout", "expiration", "login"],
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
                db.active_sessions.create_index([("user_id", ASCENDING)], name="idx_user_id")

                 # 🔍 Consultas por dispositivo + usuario
                db.active_sessions.create_index([("user_id", ASCENDING), ("device_id", ASCENDING)], name="idx_user_device_id")

                 # ⚠️ Buscar sesiones activas rápido
                db.active_sessions.create_index([("status", ASCENDING), ("is_revoked", ASCENDING)], name="idx_status_revoked")

                 # 📅 Orden por fecha de login (útil para paneles)
                db.active_sessions.create_index([("login_at", DESCENDING)], name="idx_login_at")

                 # 🔐 Índice para revocar tokens por refresh_token
                db.active_sessions.create_index([("refresh_token", ASCENDING)], unique=True, name="idx_refresh_token")

                 # ⚙️ Índice compuesto para filtros complejos (opcional)
                db.active_sessions.create_index([("user_id", ASCENDING), ("status", ASCENDING), ("is_revoked", ASCENDING)], name="idx_user_id_status_revoked")
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
        elif "items" not in db.list_collection_names():
            db.create_collection(
                "items",
                validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "name", "created_at", "updated_at"],
                        "properties": {
                            "user_id": {
                                "bsonType": "objectId",
                                "description": "ID del usuario propietario (ObjectId requerido)"
                            },
                            "name": {
                                "bsonType": "string",
                                "description": "Nombre del item"
                            },
                            "description": {
                                "bsonType": ["string", "null"],
                                "description": "Descripción opcional"
                            },
                            "created_at": {
                                "bsonType": "date",
                                "description": "Fecha de creación"
                            },
                            "updated_at": {
                                "bsonType": "date",
                                "description": "Última actualización"
                            }
                        }
                    }
                },
                validationLevel="strict",
                validationAction="error"
            )
            try:
                db.items.create_index([("user_id", ASCENDING)], name="idx_user_id")
                ic("Índice único 'user_id' creado")
            except errors.OperationFailure as e:
                ic(f"Error creando índice: {e}")
            ic("Colección 'token_blacklist' creada")
        elif "performance_metrics_api" not in db.list_collection_names():
            db.create_collection("performance_metrics_api")
            try:
                # 🔹 Crear índices
                db.performance_metrics_api.create_index(
                    [("role", ASCENDING), ("category", ASCENDING)],
                    name="idx_perf_role_category"
                )
                db.performance_metrics_api.create_index(
                    [("ts", ASCENDING)],
                    name="idx_perf_ts"
                )
                ic("Índice único 'user_id' creado")
            except errors.OperationFailure as e:
                ic(f"Error creando índice: {e}")
            ic("Colección 'token_blacklist' creada")
        elif "alerts" not in db.list_collection_names():
            db.create_collection("alerts")
            try:
                # 🔹 Crear índices
                db.alerts.create_index([("timestamp", DESCENDING)], name="idx_alerts_ts")
                db.alerts.create_index([("metric", ASCENDING)], name="idx_alerts_metric")
                ic("Índice único 'user_id' creado")
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
        elif "credentials" not in db.list_collection_names():
            db.create_collection("credentials", validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": [
                            "_id",
                            "raw_id",
                            "type",
                            "attestation_object",
                            "client_data_json",
                            "username",
                            "origin",
                            "device",
                            "fmt",
                            "sign_count",
                            "verified",
                            "pubkey",
                            "created_at"
                        ],
                        "properties": {
                            "_id": {"bsonType": "objectId"},
                            "raw_id": {
                                "bsonType": "string",
                                "pattern": "^[A-Za-z0-9\\-_]+={0,2}$",
                                "description": "Base64URL del identificador del credential"
                            },
                            "type": {
                                "bsonType": "string",
                                "enum": ["public-key"],
                                "description": "Tipo de credential WebAuthn"
                            },
                            "attestation_object": {
                                "bsonType": "string",
                                "description": "Objeto de attestation codificado en Base64URL"
                            },
                            "client_data_json": {
                                "bsonType": "string",
                                "description": "ClientDataJSON codificado en Base64URL"
                            },
                            "username": {
                                "bsonType": "string",
                                "description": "Nombre de usuario asociado"
                            },
                            "origin": {
                                "bsonType": "string",
                                "description": "Origen o dominio donde se registró la credencial"
                            },
                            "device": {
                                "bsonType": "string",
                                "description": "Dispositivo o descripción opcional"
                            },
                            "fmt": {
                                "bsonType": ["string", "null"],
                                "description": "Formato de attestation (packed, none, etc.)"
                            },
                            "sign_count": {
                                "bsonType": "int",
                                "minimum": 0,
                                "description": "Contador de firmas para prevenir replay attacks"
                            },
                            "verified": {
                                "bsonType": "bool",
                                "description": "Indica si la credencial fue verificada exitosamente"
                            },
                            "pubkey": {
                                "bsonType": "object",
                                "description": "Clave pública en formato COSE (dict con parámetros alg, x, y, etc.)",
                                "properties": {}
                            },
                            "user_handle": {
                                "bsonType": ["string", "null"],
                                "description": "Identificador opcional de usuario"
                            },
                            "created_at": {
                                "bsonType": "date",
                                "description": "Fecha de creación con zona horaria UTC"
                            }
                        }
                    }
                },
                validationLevel="strict",
                validationAction="error"
            )
            ic("Colección 'credentials' creada")
    except errors.CollectionInvalid as e:
        ic(f"La colección ya existe -> {e}")

def db_create_audit():
    # Generar 200 logs de prueba
    try:
        docs = []
        for _ in range(200):
            user_id = str(random.randint(1, 10))
            session_id = f"session_{random.randint(1000, 9999)}"
            event_type = random.choice(event_types)

            old_value = faker.ipv4() if event_type == "ip_change" else faker.user_agent()
            new_value = faker.ipv4() if event_type == "ip_change" else faker.user_agent()

            timestamp = faker.date_time_between(
                start_date="-30d", end_date="now", tzinfo=datetime.timezone.utc
            )

            docs.append({
                "session_id": session_id,
                "user_id": user_id,
                "event_type": event_type,
                "old_value": old_value,
                "new_value": new_value,
                "ip_address": faker.ipv4(),
                "user_agent": faker.user_agent(),
                "timestamp": timestamp
            })

        # Insertar en la colección
        db.session_audit.insert_many(docs)
        ic("✅ Datos de prueba insertados")
    except OperationFailure as e:
        ic(f"Error : {str(e)}")

def db_create_metrics():
    # Generar 200 logs de prueba
    # Simular métricas de LCP y FID para /home y /profile
    try:
        # Crear datos de prueba
        test_docs = []
        now = datetime.datetime.now(timezone.utc)

        for i in range(500):
            category = random.choice(categories)
            name = random.choice(metric_names[category])
            timestamp = now - timedelta(hours=random.randint(0, 48), minutes=random.randint(0, 59))
            doc = {
                "name": name,
                "category": category,
                "role": random.choice(roles),
                "value": round(random.uniform(0.1, 5.0), 2),  # valores entre 0.1 y 5.0
                "page": random.choice(pages),
                "url": random.choice(urls),
                "os": random.choice(oses),
                "browser": random.choice(browsers),
                "metric_id": f"test_{i}",
                "timestamp": timestamp
            }
            test_docs.append(doc)

        # Insertar en MongoDB
        col_metrics.insert_many(test_docs)
        print("Datos de prueba insertados:", len(test_docs))
    except OperationFailure as e:
        ic(f"Error : {str(e)}")
 
def db_create_audit_details():
    try:
        # --- Configuración de prueba ---
        num_users = 10
        sessions_per_user = 3
        changes_per_session = 2  # cambios múltiples por sesión
        docs = []

        for user_id in range(1, num_users + 1):
            for _ in range(sessions_per_user):
                session_id = f"session_{random.randint(1000,9999)}"
                old_ip = faker.ipv4()
                old_ua = faker.user_agent()

                # Registrar todos los cambios en un solo evento "session_update"
                change_summary = []
                timestamp = faker.date_time_between(start_date="-7d", end_date="now", tzinfo=datetime.timezone.utc)

                for _ in range(changes_per_session):
                    event_type = random.choice(["ip_change", "user_agent_change"])
                    if event_type == "ip_change":
                        new_ip = faker.ipv4()
                        change_summary.append(f"ip_address: {old_ip} → {new_ip}")
                        old_ip = new_ip
                    elif event_type == "user_agent_change":
                        new_ua = faker.user_agent()
                        change_summary.append(f"user_agent: {old_ua} → {new_ua}")
                        old_ua = new_ua

                # Documento único por sesión con todos los cambios
                doc = {
                    "session_id": session_id,
                    "user_id": str(user_id),
                    "event_type": "session_update",
                    "old_value": "",
                    "new_value": "; ".join(change_summary),
                    "ip_address": old_ip,
                    "user_agent": old_ua,
                    "timestamp": timestamp
                }

                docs.append(doc)

        # Insertar en MongoDB
        db.session_audit.insert_many(docs)
        ic(f"✅ Insertados {len(docs)} logs tipo 'session_update' con cambios múltiples por sesión")

    except OperationFailure as e:
        ic(f"Error : {str(e)}")
        
def create_mock_json_audit():
    # Generar 100 registros
    start_time = datetime.datetime(2025, 8, 10, 0, 0, 0)
    end_time = datetime.datetime(2025, 8, 29, 0, 0, 0)
    logs = []

    for i in range(200):
        session_id = f"session_{random.randint(1000,9999)}"
        user_id = f"user{random.randint(1, 20)}"
        event_type = random.choice(event_types)
        timestamp = faker.date_time_between(start_date="-7d", end_date="now", tzinfo=datetime.timezone.utc)
        ip_address = random.choice(ips) + str(random.randint(1, 254))
        user_agent = random.choice(user_agents)

        # Simulación de cambios (solo algunos eventos generan "changes")
        changes = {}
        if event_type == "ip_change":
            changes = {"ip_address": {"old": random.choice(ips) + str(random.randint(1, 254)), "new": ip_address}}
        elif event_type == "user_agent_change":
            changes = {"user_agent": {"old": random.choice(user_agents), "new": user_agent}}
        elif event_type == "revoked":
            changes = {"status": {"old": "active", "new": "revoked"}}
        elif event_type == "multiple_attempts":
            changes = {"attempts": {"old": str(random.randint(1, 3)), "new": str(random.randint(4, 6))}}
        elif event_type == "expiration":
            changes = {"exp": {"old": start_time, "new": end_time}}
        elif event_type == "login":
            changes = {"access": {"old": start_time, "new": end_time}}
        elif event_type == "refresh_token":
            changes = {"attempts": {"old": str(random.randint(1, 3)), "new": str(random.randint(4, 6))}}

        logs.append({
            "session_id": session_id,
            "user_id": str(user_id),
            "event_type": event_type,
            "old_value": "",
            "new_value": "",
            "timestamp": timestamp,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "changes": changes
        })

    # Insertar en MongoDB
    db.session_audit.insert_many(logs)
    ic(f"✅ Insertados {len(logs)} logs tipo 'session_update' con cambios múltiples por sesión")

def create_mock_json_session():
    sessions = []
    try:
        for i in range(100):
            login_time = base_date + timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
            refresh_time = login_time + timedelta(minutes=random.randint(5, 120))
            revoked = random.choice([True, False])
            status = random.choice(statuses)
            revoked_at = refresh_time + timedelta(minutes=random.randint(1, 30)) if revoked else None
            reason = random.choice(reasons)

            session = {
                "user_id": {"$oid": f"{uuid.uuid4().hex[:24]}"},
                "device_id": str(uuid.uuid4()),
                "ip_address": f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}",
                "browser": random.choice(browsers),
                "os": random.choice(oses),
                "login_at": {"$date": login_time.isoformat() + "Z"},
                "refresh_token": f"mock_refresh_token_{i+1}",
                "is_revoked": revoked,
                "status": status,
                "revoked_at": {"$date": revoked_at.isoformat() + "Z"} if revoked else None,
                "last_refresh_at": {"$date": refresh_time.isoformat() + "Z"},
                "reason": reason,
                "role": roles
            }
            sessions.append(session)

        # Insertar en MongoDB
        db.active_sessions.insert_many(sessions)
        ic(f"✅ Insertados {len(sessions)} logs tipo 'session_update' con cambios múltiples por sesión")
    except errors.CollectionInvalid as e:
        ic(f"La colección ya existe -> {e}")
  
def create_mock_json_user():
    # Generar 100 usuarios
    users = []

    for i in range(2,100):
        user_id = uuid.uuid4().hex[:24]  # Simular ObjectId
        username = f"user{i}@{random.choice(domains)}"
        created_at = datetime.datetime(2025, 7, 1) + timedelta(days=random.randint(0, 60))
        updated_at = created_at + timedelta(minutes=random.randint(1, 5000))
        failed_attempts = random.randint(0, 2)
        blocked_until = None if failed_attempts <= 2 else (updated_at + timedelta(hours=1)).isoformat() + "Z"

        users.append({
            "username": username,
            "password": base_user["password"],  # misma hash de prueba
            "email": username,
            "rol": "User",
            "created_at": datetime.datetime.now(tz=timezone.utc),
            "updated_at": datetime.datetime.now(tz=timezone.utc),
            "failed_attempts": failed_attempts,
            "blocked_until": blocked_until
        })

    # Insertar en MongoDB
    db.users.insert_many(users)
    ic(f"✅ Insertados {len(users)}")

def db_delete_audit():
    db.session_audit.delete_many({})

def db_delete_performance_endpoint():
    db.col_metrics_api.delete_many({})
def db_create_performance_endpoint():
    now = datetime.datetime.now(timezone.utc)

    docs = []
    for i in range(200):  # 200 documentos de prueba
        role = random.choice(roles)
        url, method = random.choice(endpoints)
        ts = now - timedelta(minutes=random.randint(0, 120))  # últimas 2h
        value = round(random.uniform(50, 800), 2)  # duración ms

        docs.append({
            "type": "apiResponseTime",
            "category": "endpoint",
            "value": value,
            "url": url,
            "method": method,
            "status": random.choice(["200", "200", "200", "500"]),  # mayoría 200
            "role": role,
            "ts": ts,
        })

    db.performance_metrics_api.insert_many(docs)
    print("✅ Insertados datos de prueba:", len(docs))
# --- Función get_logs_audit ---
def get_logs_audit(user_id=None, event_type=None, start=None, end=None, page=1, limit=10) -> dict:
    page = int(1)
    limit = int(10)
    fetch_all = True

    # --- Filtros ---
    filters = {}
    if user_id:
        filters["user_id"] = user_id
    if event_type:
        filters["event_type"] = event_type
    if start or end:
        filters["timestamp"] = {}
        if start:
            filters["timestamp"]["$gte"] = start
        if end:
            filters["timestamp"]["$lte"] = end

    # --- Pipeline ---
    pipeline = [{"$match": filters}]

    # Campo dinámico "changes"
    pipeline.append({
        "$addFields": {
            "changes": {
                "$let": {
                    "vars": {
                        "allFields": {
                            "$mergeObjects": [
                                {"old_value": {"old": "$old_value", "new": "$new_value"}},
                                {"ip_address": {"old": "$old_ip", "new": "$ip_address"}},
                                {"user_agent": {"old": "$old_user_agent", "new": "$user_agent"}},
                            ]
                        }
                    },
                    "in": {
                        "$arrayToObject": {
                            "$filter": {
                                "input": {"$objectToArray": "$$allFields"},
                                "as": "field",
                                "cond": {
                                    "$ne": [
                                        {"$ifNull": ["$$field.v.old", None]},
                                        {"$ifNull": ["$$field.v.new", None]},
                                    ]
                                },
                            }
                        }
                    },
                }
            }
        }
    })

    # --- Paginación o no ---
    if fetch_all:
        # Devuelve todo sin skip/limit
        pipeline.append({
            "$project": {
                "_id": 0,
                "session_id": 1,
                "user_id": 1,
                "event_type": 1,
                "old_value": 1,
                "new_value": 1,
                "ip_address": 1,
                "user_agent": 1,
                "timestamp": 1,
                "changes": 1,
            }
        })
    else:
        skip = (page - 1) * limit
        pipeline.append({
            "$facet": {
                "data": [
                    {"$skip": skip},
                    {"$limit": limit},
                    {
                        "$project": {
                            "_id": 0,
                            "session_id": 1,
                            "user_id": 1,
                            "event_type": 1,
                            "old_value": 1,
                            "new_value": 1,
                            "ip_address": 1,
                            "user_agent": 1,
                            "timestamp": 1,
                            "changes": 1,
                        }
                    },
                ],
                "totalCount": [{"$count": "count"}],
            }
        })

    result = list(db.session_audit.aggregate(pipeline=pipeline))

    if fetch_all:
        logs = result
        total_count = len(logs)
    else:
        data = result[0] if result else {"data": [], "totalCount": []}
        logs = data.get("data", [])
        total_count = data.get("totalCount", [{}])
        total_count = total_count[0].get("count", 0) if total_count else 0

    # Normalizar timestamps a ISO
    for log in logs:
        if isinstance(log.get("timestamp"), datetime.datetime):
            log["timestamp"] = log["timestamp"].isoformat()

    return {
        "logs": logs,
        "total_count": total_count,
        "page": page if not fetch_all else 1,
        "limit": limit if not fetch_all else total_count,
    }

def get_all_users() -> dict:
        pipeline = [
            {"$match": {"rol": {"$ne": "Admin"}}},
            {"$sort": SON([("username", 1)])},
            {
                "$project": {
                    "_id": 0,
                    "username": 1,
                    "rol": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "failed_attempts": 1,
                    "blocked_until": 1
                }
            }
        ]

        result = list(db.users.aggregate(pipeline=pipeline))
        logs = result
        total_count = len(logs)
        # Normalizar timestamps a ISO
        for log in logs:
            if isinstance(log.get("create_at"), datetime.datetime):
                log["create_at"] = log["create_at"].isoformat()
            if isinstance(log.get("update_at"), datetime.datetime):
                log["update_at"] = log["update_at"].isoformat()
        ic(logs)
        ic(total_count)
        return {
            "logs": logs,
            "total_count": total_count
        }
def get_all_users_items() -> dict:
    # Pipeline
    pipeline = [
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_item"
            }
        },
        {"$unwind": "$user_item"},
        {"$match": {"user_id": user_oid}},
        {
            "$project": {
                "_id": 1,
                "user_id": 1,
                "name": 1,
                "description": 1,
                "created_at": 1,
                "updated_at": 1,
                "user_item.username": 1   # ejemplo de campo de users
            }
        }
    ]
    ic(type(pipeline))
    # Ejecutar aggregate
    results = list(db["items"].aggregate(pipeline))

    # Mostrar resultados
    for doc in results:
        print(doc)
def aggregate_timeline(role: str,
            category: str,
            interval: str,
            limit: int,
            group_by_endpoint: bool
        ):
        group_format = {
            "minute": {"$dateTrunc": {"date": "$timestamp", "unit": "minute"}},
            "hour": {"$dateTrunc": {"date": "$timestamp", "unit": "hour"}},
            "day": {"$dateTrunc": {"date": "$timestamp", "unit": "day"}},
        }[interval]

        match = {"category": category}
        if role:
            match["role"] = role

        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": {
                    "bucket": group_format,
                    "url": "$url",
                    "method": "$name"  # en tu SQL era "name" → método
                },
                "avg": {"$avg": "$value"},
                "min": {"$min": "$value"},
                "max": {"$max": "$value"},
                "count": {"$sum": 1}
            }},
            {"$sort": SON([("_id.bucket", 1)])},
            {"$limit": limit * 5}  # para cubrir varios endpoints por bucket
        ]

        result = db["metrics"].aggregate(pipeline=pipeline)

        grouped = {}
        for r in result:
            bucket = r["_id"]["bucket"].isoformat() + "Z"
            grouped.setdefault(bucket, []).append({
                "url": r["_id"]["url"],
                "method": r["_id"]["method"],
                "avg": r["avg"],
                "min": r["min"],
                "max": r["max"],
                "count": r["count"]
            })

        return grouped
# Obtener métricas por URL
def get_timeline(role="User",
            category="endpoint",
            interval="hour",
            limit=10,
            group_by_endpoint=True) -> dict[str,list]:
        raw = aggregate_timeline(role, category, interval, limit, group_by_endpoint)
        timeline = []
        for bucket, rows in raw.items():
            metrics = []
            for r in rows:
                metrics.append({
                    "url": r.get("url"),
                    "method": r.get("method", "GET"),
                    "avg": round(r.get("avg", 0), 2),
                    "min": round(r.get("min", 0), 2),
                    "max": round(r.get("max", 0), 2),
                    "count": r.get("count", 0),
                })
            timeline.append({
                "bucket": bucket,
                "metrics": metrics
            })

        # Ordenar por fecha ascendente
        timeline.sort(key=lambda x: x["bucket"])
        return timeline

def find(query=None, sort=None, limit=None):
    """Consulta genérica"""
    cursor = db.metrics.find(query=query or {}, projection={})
    if sort:
        cursor = cursor.sort(sort)
    if limit:
        cursor = cursor.limit(limit)
    return list(cursor)
def find_alerts_since(cutoff):
    query = {"category": "alert", "timestamp": {"$gte": cutoff}}
    sort = {"$sort": SON([("timestamp", -1)])}
    return find(query=query,sort=sort)
def get_recent_alerts(minutes=60):
    """
    Devuelve alertas recientes. 
    Formato esperado por JS:
    [
        {"timestamp": "2025-09-18T21:00:00Z", "level": "error", "message": "Timeout en /api/profile"}
    ]
    """
    cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=minutes)
    docs = find_alerts_since(cutoff)

    alerts = []
    for d in docs:
        alerts.append({
            "timestamp": d["timestamp"].isoformat() + "Z",
            "level": d.get("level", "warning"),
            "message": d.get("message", "alerta sin detalle")
        })
    return alerts
def get_metrics_timeline_endpoint(
            role="User",
            category="endpoint",
            interval="hour",
            limit=10,
            group_by_endpoint=True
        ):
        if interval == "day":
            date_format = "%Y-%m-%d"
        elif interval == "hour":
            date_format = "%Y-%m-%dT%H:00:00Z"
        else:
            raise ValueError("Intervalo no soportado")

        pipeline = [
            {
                "$group": {
                    "_id": {
                        "bucket": {
                            "$dateToString": {
                                "format": date_format,
                                "date": "$ts"
                            }
                        },
                        "url": "$url",
                        "method": "$method"
                    },
                    "avg": {"$avg": "$value"},
                    "min": {"$min": "$value"},
                    "max": {"$max": "$value"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id.bucket": 1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "bucket": "$_id.bucket",
                    "url": "$_id.url",
                    "method": "$_id.method",
                    "avg": {"$round": ["$avg", 2]},
                    "min": {"$round": ["$min", 2]},
                    "max": {"$round": ["$max", 2]},
                    "count": 1
                }
            }
        ]

        results = list(col_metrics_api.aggregate(pipeline=pipeline))
        return {"series": results}
def logs_result():
    # --- Prueba de consulta ---
    print("\n--- Logs consolidados de usuario 2 ---")
    result = get_logs_audit()
    ic(result)

    print(f"\nTotal de logs encontrados: {result['total_count']}")

def main():
    # db_delete_audit()
    # create_mock_json_audit()
    # Generar 1000 documentos
    db_create_collection()
    # db_delete_performance_endpoint()
    # ic(get_metrics_timeline())
    # db_create_audit()
    # db_create_audit_details()

if __name__ == "__main__":
    main()


