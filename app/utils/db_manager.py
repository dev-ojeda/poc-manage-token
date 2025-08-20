#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, timezone
from flask import Blueprint, request

from app.utils.db_mongo import MongoDatabase
from app.model.token_generator import TokenGenerator

db_Manager_bp = Blueprint("dbManager", __name__)

class DbManager:
    def __init__(self):
        self.conexion = MongoDatabase()
        self.generate_token = TokenGenerator()
        self.refresh_tokens = "refresh_tokens"
        self.token_blacklist = "token_blacklist"
        self.global_tokens = "global_tokens"
        self.session_audit = "session_audit"
        self.active_sessions = "active_sessions"
   
    def get_active_devices(self,username: str):
        devices = self.conexion.find(self.refresh_tokens,
            {"username": username, "revoked_at": None, "expires_at": {"$gt": datetime.now(timezone.utc)}},
            {"_id": 0, "device_id": 1, "user_agent": 1, "ip_address": 1, "expires_at": 1}
        )
        return list(devices)

    def update_store_refresh_token_revoked(self, username: str, device_id: str) -> dict:
        return self.conexion.update_with_log(self.refresh_tokens,
            {"username": username, "device_id": device_id },
            {
                "$set": {
                    "revoked_at": datetime.now(timezone.utc)
                }
            },
            upsert=True,
            context="Revocar Refresh Token"
        )   
    def is_valid_refresh_token(self, refresh_token: str, device_id: str) -> bool:
        token = self.conexion.find_one(
            self.refresh_tokens,
            {
                "refresh_token": refresh_token,
                "device_id": device_id,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            }
        )

        if not token or token.get("revoked_at"):
            return False

        return True  # Válido
    
    def get_refresh_token(self, refresh_token: str) -> dict | None:
        query = {"refresh_token": refresh_token}
        doc = self.conexion.find_one(self.refresh_tokens, query)
        return doc 
                                     
    def revoke_tokens_by_device(self, device_id: str) -> int:
        update = {
            "$set": {
                "revoked_at": datetime.now(timezone.utc)
            }
        }
        return self.conexion.update_many(self.refresh_tokens, {"device_id": device_id}, update)
    
    def exists_token_global(self) -> dict:
        is_valido = bool(self.conexion.count_documents(self.global_tokens,filtro={}))
        if not is_valido:
            global_token = self.generate_token.create_tokens_global()
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/138.0.0.0 Safari/537.36"
            ip = request.remote_addr
            result = self.conexion.insert_with_log(self.global_tokens,{
                "token": global_token,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=60),
                "ip_address": ip,
                "user_agent": user_agent
            },context="Insertar Token Global")
            return self.conexion.find_one(self.global_tokens,
                    { "_id": result.get("inserted_id") },
                    projection={
                        "_id": 0,
                        "token": 1,
                        "created_at": 1,
                        "expires_at": 1,
                        "ip_address": 1,
                        "user_agent": 1
                    }
            )
            # Convertir a lista de strings
        else:
            return self.conexion.find_one(self.global_tokens,
                   {"expires_at": {"$gt": datetime.now(timezone.utc)}},
                    projection={
                        "_id": 0,
                        "token": 1,
                        "created_at": 1,
                        "expires_at": 1,
                        "ip_address": 1,
                        "user_agent": 1
                    })
    def get_active_sessions_since(self, user_id, ip_address=None, since=None) -> list[dict]:
        """
        Devuelve las sesiones activas modificadas después de un timestamp dado.
        """
        query = {
            "user_id": user_id,
            "is_revoked": False
        }

        if ip_address:
            query["ip_address"] = ip_address

        if since:
            if isinstance(since, str):
                since = datetime.fromisoformat(since)
            query["last_refresh_at"] = {"$gte": since}

        projection = {
            "_id": 0,
            "device_id": 1,
            "ip_address": 1,
            "user_agent": 1,
            "login_at": 1,
            "last_refresh_at": 1
        }

        return list(self.conexion.find(self.active_sessions, query, projection).sort("last_refresh_at", -1))

    # return list(self.conexion.find(self.refresh_tokens, query, projection))
    def log_audit_event(self, 
                        session_id: str, 
                        user_id: str, 
                        event_type: str,
                        old_value: str, 
                        new_value: str,
                        ip_address: str = None, 
                        user_agent: str = None):
        """
        Registra un evento de auditoría en la colección session_audit.

        :param db: Instancia de la base de datos MongoDB.
        :param session_id: ID de la sesión afectada.
        :param user_id: ID del usuario afectado.
        :param event_type: Tipo de evento ('ip_change', 'user_agent_change', 'revoked', etc.).
        :param old_value: Valor anterior del campo modificado.
        :param new_value: Valor nuevo del campo.
        :param ip_address: IP actual (opcional).
        :param user_agent: User-Agent actual (opcional).
        """
        event = {
            "session_id": session_id,
            "user_id": user_id,
            "event_type": event_type,
            "old_value": old_value,
            "new_value": new_value,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc)
        }
        self.conexion.insert_one(self.session_audit, event)

    def get_datetime_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def update_datetime_format_iso(self, fecha: datetime) -> datetime:
        return fecha.fromisoformat(fecha.isoformat())