#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import PyMongoError, NetworkTimeout
from app.config import Config

class MongoDatabase:
    def __init__(self, retry: int = 3, backoff: float = 0.5) -> None:
        self.db_name = Config.MONGO_DB
        self.uri = Config.MONGO_URI_CLUSTER_X509
        self.tls_certificate_key_file = Config.MONGODB_X509
        self.client: Optional[MongoClient] = None
        self.db = None
        self.retry = retry
        self.backoff = backoff

        # Logger centralizado
        self.logger = logging.getLogger("MongoDatabase")
        self.logger.setLevel(logging.INFO)

        # Conectar automáticamente
        self.connect()

    # --- Context manager ---
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback_info):
        self.close()

    # --- Conexión ---
    def connect(self) -> None:
        try:
            self.client = MongoClient(
                self.uri,
                tls=True,
                tlsCertificateKeyFile=self.tls_certificate_key_file,
                server_api=ServerApi('1'),
                tz_aware=True,
                maxPoolSize=50,
                minPoolSize=5,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
            )
            self.db = self.client[self.db_name]
            self.logger.info(f"Conectado a MongoDB -> {self.db_name}")
        except (PyMongoError, NetworkTimeout) as e:
            self.logger.error(f"❌ Error al conectar a MongoDB: {e}")
            raise

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.logger.info("Conexión a MongoDB cerrada")

    # --- Helper ObjectId ---
    @staticmethod
    def _convert_objectid(doc: dict) -> dict:
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                doc[k] = str(v)
        return doc

    # --- Access collection ---
    def _get_collection(self, name: str):
        if not self.db:
            raise RuntimeError("MongoDB no está conectado")
        return self.db[name]

    # --- Retry decorator interno ---
    def _retry(func):
        def wrapper(self, *args, **kwargs):
            attempts = 0
            while True:
                try:
                    return func(self, *args, **kwargs)
                except PyMongoError as e:
                    attempts += 1
                    if attempts > self.retry:
                        self.logger.error(f"[{func.__name__}] Excedido máximo retries: {e}")
                        return {"success": False, "error": str(e)}
                    self.logger.warning(f"[{func.__name__}] Retry {attempts}/{self.retry} tras error: {e}")
                    time.sleep(self.backoff)
        return wrapper

    # --------------------------
    # CREATE
    # --------------------------
    @_retry
    def insert_one(self, collection: str, document: Dict[str, Any], context: str = "") -> dict:
        try:
            col = self._get_collection(collection)
            result = col.insert_one(document)
            self.logger.info(f"[{context}] Inserted into {collection}: {result.inserted_id}")
            return {"success": True, "inserted_id": str(result.inserted_id), "context": context}
        except PyMongoError as e:
            self.logger.error(f"[{context}] insert_one failed: {e}")
            return {"success": False, "error": str(e), "context": context}

    @_retry
    def insert_many(self, collection: str, documents: List[Dict[str, Any]], context: str = "") -> dict:
        try:
            col = self._get_collection(collection)
            result = col.insert_many(documents)
            self.logger.info(f"[{context}] Inserted {len(result.inserted_ids)} docs into {collection}")
            return {"success": True, "inserted_ids": [str(_id) for _id in result.inserted_ids], "context": context}
        except PyMongoError as e:
            self.logger.error(f"[{context}] insert_many failed: {e}")
            return {"success": False, "error": str(e), "context": context}

    # --------------------------
    # READ
    # --------------------------
    @_retry
    def find_one(
        self,
        collection: str,
        filtro: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None,
        context: str = ""
    ) -> dict:
        try:
            col = self._get_collection(collection)
            doc = col.find_one(filtro, projection)
            if doc:
                doc = self._convert_objectid(doc)
            return {"success": True, "data": doc, "context": context}
        except PyMongoError as e:
            self.logger.error(f"[{context}] find_one failed: {e}")
            return {"success": False, "error": str(e), "context": context}

    @_retry
    def find_many(
        self,
        collection: str,
        filtro: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None,
        limit: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None,
        context: str = ""
    ) -> dict:
        try:
            col = self._get_collection(collection)
            cursor = col.find(filtro, projection)
            if sort:
                cursor = cursor.sort(sort)
            if limit > 0:
                cursor = cursor.limit(limit)
            results = [self._convert_objectid(doc) for doc in cursor]
            return {"success": True, "data": results, "count": len(results), "context": context}
        except PyMongoError as e:
            self.logger.error(f"[{context}] find_many failed: {e}")
            return {"success": False, "error": str(e), "context": context}

    @_retry
    def count_documents(self, collection: str, filtro: Dict[str, Any], context: str = "") -> dict:
        try:
            col = self._get_collection(collection)
            count = col.count_documents(filtro)
            return {"success": True, "count": count, "context": context}
        except PyMongoError as e:
            self.logger.error(f"[{context}] count_documents failed: {e}")
            return {"success": False, "error": str(e), "context": context}

    @_retry
    def aggregate(self, collection: str, pipeline: Any, context: str = "") -> dict:
        try:
            docs = list(self.db[collection].aggregate(pipeline=pipeline))
            results = [self._convert_objectid(doc) for doc in docs]
            return {"success": True, "data": results, "context": context}
        except PyMongoError as e:
            self.logger.error(f"[{context}] aggregate failed: {e}")
            return {"success": False, "error": str(e), "context": context}

    # --------------------------
    # UPDATE
    # --------------------------
    @_retry
    def update_one(self, collection: str, filtro: Dict[str, Any], update: Dict[str, Any], upsert: bool = False, context: str = "") -> dict:
        try:
            col = self._get_collection(collection)
            result = col.update_one(filtro, {"$set": update}, upsert=upsert)
            return {"success": True, "matched_count": result.matched_count, "modified_count": result.modified_count, "context": context}
        except PyMongoError as e:
            self.logger.error(f"[{context}] update_one failed: {e}")
            return {"success": False, "error": str(e), "context": context}

    @_retry
    def upsert_one(self, collection: str, filtro: Dict[str, Any], update: Dict[str, Any], context: str = "") -> dict:
        return self.update_one(collection, filtro, update, upsert=True, context=context)

    # --------------------------
    # DELETE
    # --------------------------
    @_retry
    def delete_one(self, collection: str, filtro: Dict[str, Any], context: str = "") -> dict:
        try:
            col = self._get_collection(collection)
            result = col.delete_one(filtro)
            return {"success": True, "deleted_count": result.deleted_count, "context": context}
        except PyMongoError as e:
            self.logger.error(f"[{context}] delete_one failed: {e}")
            return {"success": False, "error": str(e), "context": context}

    # --------------------------
    # Check connection
    # --------------------------
    def ping(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            self.logger.error(f"Ping MongoDB falló: {e}")
            return False
