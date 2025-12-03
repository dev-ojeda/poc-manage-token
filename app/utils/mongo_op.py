#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
mongo_op.py
------------
Helper centralizado para ejecutar operaciones MongoDB seguras,
con manejo de errores, logging, reconexión automática y sesiones.
"""

import datetime
from pymongo.errors import PyMongoError, ConnectionFailure
from bson import ObjectId
from typing import Any, Dict, List, Optional
from app.utils.db_mongo import MongoDatabase
from app.logging_config import get_logger


class MongoOp:
    def __init__(self):
        self.db_instance = MongoDatabase()
        self.logger = get_logger(self.__class__.__name__)

    # -----------------------------
    # UTILIDAD CENTRALIZADA DE RESPUESTA
    # -----------------------------
    def _response(self, success: bool, context: str, data: Any = None, error: str = None) -> dict:
        return {
            "success": success,
            "context": context,
            "data": data if data is not None else None,
            "error": error
        }

    # -----------------------------
    # ENVOLTORIO RESILIENTE
    # -----------------------------
    def _safe_op(self, func, context: str):
        try:
            if not self.db_instance.is_connected():
                self.logger.warning(f"{context}: Mongo desconectado, intentando reconexión…")
                if not self.db_instance.reconnect():
                    raise ConnectionFailure("No se pudo reconectar con MongoDB.")
            return func()
        except (ConnectionFailure, PyMongoError) as e:
            self.logger.error(f"{context} → Error de conexión: {e}")
            if self.db_instance.reconnect():
                self.logger.info(f"{context} → Reintentando tras reconexión exitosa.")
                return func()
            raise
        except Exception as e:
            self.logger.exception(f"{context} → Error inesperado: {e}")
            raise

    @staticmethod
    def _now() -> datetime.datetime:
        return datetime.datetime.now(tz=datetime.timezone.utc)

    # -----------------------------
    # OPERACIONES CRUD
    # -----------------------------
    def insert_one(self, collection, document: Dict[str, Any], *, context: str = "insert_one") -> dict:
        return self._safe_op(lambda: self._insert_one_raw(collection, document, context), context)

    def _insert_one_raw(self, collection, document, context):
        with self.db_instance.start_session() as session:
            result = collection.insert_one(document, session=session)
            self.logger.info(f"🟢 [{context}] Insertado ID={result.inserted_id}")
            return self._response(True, context, {"inserted_id": str(result.inserted_id)})

    def find_one(self, collection, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None, *, context: str = "find_one") -> dict:
        return self._safe_op(lambda: self._find_one_raw(collection, query, projection, context), context)

    def _find_one_raw(self, collection, query, projection, context):
        result = collection.find_one(query, projection)
        if result and "_id" in result:
            result["_id"] = str(result["_id"])
        else:
            result = None
        return self._response(True, context, result)

    def find_many(self, collection, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None, *, context: str = "find_many") -> dict:
        return self._safe_op(lambda: self._find_many_raw(collection, query, projection, context), context)

    def _find_many_raw(self, collection, query, projection, context):
        results = list(collection.find(query, projection))
        for r in results:
            r["_id"] = str(r["_id"])
        return self._response(True, context, results)

    def update_one(self, collection, query: Dict[str, Any], update: Dict[str, Any], *, context: str = "update_one") -> dict:
        return self._safe_op(lambda: self._update_one_raw(collection, query, update, context), context)

    def _update_one_raw(self, collection, query, update, context):
        with self.db_instance.start_session() as session:
            result = collection.update_one(query, update, session=session)
            modified = result.modified_count > 0
            self.logger.info(f"🟡 [{context}] Modificados={result.modified_count}")
            return self._response(True, context, {"modified": modified})

    def delete_one(self, collection, query: Dict[str, Any], *, context: str = "delete_one") -> dict:
        return self._safe_op(lambda: self._delete_one_raw(collection, query, context), context)

    def _delete_one_raw(self, collection, query, context):
        with self.db_instance.start_session() as session:
            result = collection.delete_one(query, session=session)
            deleted = result.deleted_count > 0
            self.logger.info(f"🔴 [{context}] Eliminados={result.deleted_count}")
            return self._response(True, context, {"deleted": deleted})

    def replace_one(self, collection, query: Dict[str, Any], new_doc: Dict[str, Any], *, context: str = "replace_one") -> dict:
        return self._safe_op(lambda: self._replace_one_raw(collection, query, new_doc, context), context)

    def _replace_one_raw(self, collection, query, new_doc, context):
        with self.db_instance.start_session() as session:
            result = collection.replace_one(query, new_doc, session=session)
            replaced = result.modified_count > 0
            self.logger.info(f"🧩 [{context}] Documento reemplazado: {replaced}")
            return self._response(True, context, {"replaced": replaced})

    def aggregate(self, collection, pipeline: List[Dict[str, Any]], *, context: str = "aggregate") -> dict:
        return self._safe_op(lambda: self._aggregate_raw(collection, pipeline, context), context)

    def _aggregate_raw(self, collection, pipeline, context):
        cursor = collection.aggregate(pipeline)
        data = list(cursor)
        for item in data:
            if "_id" in item and isinstance(item["_id"], ObjectId):
                item["_id"] = str(item["_id"])
        self.logger.debug(f"📊 [{context}] Resultados: {len(data)} documentos.")
        return self._response(True, context, data)

    def count(self, collection, query: Dict[str, Any], *, context: str = "count") -> dict:
        return self._safe_op(lambda: self._count_raw(collection, query, context), context)

    def _count_raw(self, collection, query, context):
        count = collection.count_documents(query)
        return self._response(True, context, {"count": count})

    # -----------------------------
    # UPSERT GENÉRICO (para refresh tokens)
    # -----------------------------
    def upsert(self, collection, query: dict, update: dict, *, context: str = "upsert") -> dict:
        return self._safe_op(lambda: self._upsert_raw(collection, query, update, context), context)

    def _upsert_raw(self, collection, query, update, context):
        with self.db_instance.start_session() as session:
            result = collection.update_one(query, update, upsert=True, session=session)
            upserted = result.modified_count > 0 or result.upserted_id is not None
            self.logger.info(f"🟠 [{context}] Documento upsert: {upserted}, ID={result.upserted_id}")
            return self._response(
                True,
                context,
                {"upserted": upserted, "id": str(result.upserted_id) if result.upserted_id else None}
            )

    # -----------------------------
    # UPSERT ESPECÍFICO PARA REFRESH TOKEN
    # -----------------------------
    def upsert_refresh_token(
        self,
        collection,
        **kwargs
    ) -> dict:
  
        # Query para buscar documento existente
        query = {"username": kwargs["username"], "device_id": kwargs["device_id"]}
        now = self._now()
        # Campos a actualizar
        update_fields = {
            "jti": kwargs["jti"],
            "refresh_token":  kwargs["refresh_token"],
            "update_at": now,
            "expires_at": now + datetime.timedelta(minutes=4),
            "revoked_at": None,
            "used_at": None,
            "refresh_attempts": kwargs["refresh_attempts"],
            "browser": kwargs["user_agent"]["browser"],
            "os": kwargs["user_agent"]["os"],
            "user_agent": f"{kwargs["user_agent"]["browser"]} - {kwargs["user_agent"]["os"]}",
            "ip_address": kwargs["ip_address"],
        }


        # Campos solo al insertar
        set_on_insert = {
            "username": kwargs["username"],
            "device_id": kwargs["device_id"],
            "created_at": now,
        }

        update = {"$set": update_fields, "$setOnInsert": set_on_insert}

        return self.upsert(collection, query, update, context="upsert_refresh_token")

# Singleton global reutilizable
mongo_op = MongoOp()
