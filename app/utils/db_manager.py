#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta, timezone
from typing import Dict, Any

from flask import Blueprint
from app.utils.db_mongo import MongoDatabase
from app.model.token_generator_model import TokenGeneratorModel

db_Manager_bp = Blueprint("dbManager", __name__)


class DbManager:
    """
    Servicio para manejo de tokens globales.
    """

    TOKEN_EXPIRATION_MINUTES = 60

    def __init__(self, db: MongoDatabase = None, token_generator: TokenGeneratorModel = None):
        self.db = db or MongoDatabase()
        self.token_generator = token_generator or TokenGeneratorModel()
        self.collection_name = "global_tokens"

    # --------------------------
    # Gestión de token global
    # --------------------------
    def get_or_create_global_token(self, ip: str, user_agent: str) -> Dict[str, Any]:
        """
        Retorna un token global activo si existe, o crea uno nuevo.
        """
        # Buscar token activo
        now = self._now()
        pipeline = [
            {"$match": {"expires_at": {"$gt": now}}},
            {"$project": {"_id": 0, "token": 1, "created_at": 1, "expires_at": 1, "ip_address": 1, "user_agent": 1}},
            {"$limit": 1}
        ]
        existing_token = self.db.aggregate(self.collection_name, pipeline=pipeline)
        existing_token = existing_token[0] if existing_token else None
        if existing_token:
            return existing_token

        # Crear token si no existe
        token = self.token_generator.create_tokens_global()
        insert_result = self.db.insert_with_log(
            collection=self.collection_name,
            document={
                "token": token,
                "created_at": now,
                "expires_at": now + timedelta(minutes=self.TOKEN_EXPIRATION_MINUTES),
                "ip_address": ip,
                "user_agent": user_agent
            },
            context="Insertar Token Global"
        )

        return {
            "success": True,
            "token": token,
            "context": "CREATE_TOKEN",
            "inserted": insert_result
        }

    # --------------------------
    # Helpers de fecha
    # --------------------------
    @staticmethod
    def _now() -> datetime.datetime:
        """Devuelve la fecha/hora actual en UTC."""
        return datetime.datetime.now(tz=timezone.utc)

    @staticmethod
    def isoformat_datetime(fecha: datetime.datetime) -> datetime.datetime:
        """Normaliza un datetime a formato ISO."""
        return fecha.fromisoformat(fecha.isoformat())
