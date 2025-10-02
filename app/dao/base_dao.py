import logging
import time
from typing import Any, Dict, List, Optional
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.client_session import ClientSession
from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult
from app.utils.db_mongo import MongoDatabase
from app.utils.db_operations import mongo_op


class BaseDAO:
    COLLECTION: str = ""

    def __init__(self, db: Optional[MongoDatabase] = None, collection_name: Optional[str] = None):
        self.db = db or MongoDatabase()
        self.collection_name = collection_name or self.COLLECTION
        if not self.collection_name:
            raise ValueError("Se requiere collection_name o definir BaseDAO.COLLECTION")
        self.logger = logging.getLogger(f"DAO.{self.__class__.__name__}")

    def _get_collection(self) -> Collection:
        return self.db._get_collection(self.collection_name)

    def _convert_objectid(self, doc: dict) -> dict:
        """Convierte ObjectId a str para JSON"""
        if not doc:
            return doc
        for k, v in doc.items():
            if hasattr(v, 'binary') or isinstance(v, ObjectId):
                doc[k] = str(v)
            elif isinstance(v, dict):
                doc[k] = self._convert_objectid(v)
            elif isinstance(v, list):
                doc[k] = [self._convert_objectid(i) if isinstance(i, dict) else i for i in v]
        return doc

    # --------------------------
    # SESSION / TRANSACTION
    # --------------------------
    def start_session(self) -> ClientSession:
        return self.db.client.start_session()

    def with_transaction(self, func, *args, **kwargs):
        """Ejecuta una función dentro de una transacción"""
        with self.start_session() as session:
            try:
                result = session.with_transaction(lambda s: func(*args, session=s, **kwargs))
                return result
            except Exception as e:
                self.logger.exception(f"Transaction failed: {e}")
                return {"success": False, "data": None, "context": kwargs.get("context", "Transaction"), "message": str(e)}

    # --------------------------
    # CREATE
    # --------------------------
    @mongo_op(backoff=1, max_attempts=5)
    def insert_one(self, document: dict, context: str = "", session: Optional[ClientSession] = None) -> dict:
        col = self._get_collection()
        result: InsertOneResult = col.insert_one(document, session=session)
        msg = f"[{context}] Documento insertado: {result.inserted_id}" if result.acknowledged else f"[{context}] Inserción sin confirmación"
        self.logger.info(msg)
        return {
            "success": result.acknowledged,
            "data": self._convert_objectid(document),
            "context": context,
            "message": msg
        }

    @mongo_op(backoff=1, max_attempts=5)
    def insert_many(self, documents: List[dict], context: str = "", session: Optional[ClientSession] = None) -> dict:
        col = self._get_collection()
        result: InsertManyResult = col.insert_many(documents, session=session)
        msg = f"[{context}] Insertados {len(result.inserted_ids)} documentos"
        self.logger.info(msg)
        converted_docs = [self._convert_objectid(doc) for doc in documents]
        return {
            "success": True,
            "data": converted_docs,
            "context": context,
            "message": msg
        }

    # --------------------------
    # READ
    # --------------------------
    @mongo_op(backoff=1, max_attempts=5)
    def find_one(self, query: dict = None, projection: dict = None, context: str = "", session: Optional[ClientSession] = None) -> dict:
        col = self._get_collection()
        doc = col.find_one(query or {}, projection, session=session)
        return {
            "success": doc is not None,
            "data": self._convert_objectid(doc) if doc else None,
            "context": context,
            "message": f"[{context}] Documento encontrado" if doc else f"[{context}] No se encontró documento"
        }

    @mongo_op(backoff=1, max_attempts=5)
    def find(self, query: dict = None, projection: dict = None, context: str = "", session: Optional[ClientSession] = None) -> dict:
        col = self._get_collection()
        cursor = col.find(query or {}, projection or {}, session=session)
        docs = [self._convert_objectid(doc) for doc in cursor]
        msg = f"[{context}] {len(docs)} documentos encontrados"
        self.logger.info(msg)
        return {"success": True, "data": docs, "context": context, "message": msg}

    @mongo_op(backoff=1, max_attempts=5)
    def aggregate(self, pipeline: List[dict], context: str = "", session: Optional[ClientSession] = None) -> dict:
        col = self._get_collection()
        try:
            cursor = col.aggregate(pipeline, session=session)
            results = [self._convert_objectid(doc) for doc in cursor]
            msg = f"[{context}] {len(results)} documentos agregados"
            self.logger.info(msg)
            return {"success": True, "data": results, "context": context, "message": msg}
        except Exception as e:
            self.logger.exception(f"[{context}] Error en aggregate: {e}")
            return {"success": False, "data": [], "context": context, "message": str(e)}

    # --------------------------
    # UPDATE
    # --------------------------
    @mongo_op(backoff=1, max_attempts=5)
    def update_one(self, query: dict, update: dict, upsert: bool = False, context: str = "", session: Optional[ClientSession] = None) -> dict:
        col = self._get_collection()
        result: UpdateResult = col.update_one(query, update=update, upsert=upsert, session=session)
        msg = f"[{context}] Documento actualizado correctamente" if result.modified_count else f"[{context}] Documento encontrado pero sin cambios"
        self.logger.info(msg)
        return {
            "success": result.matched_count >= 0,
            "data": {"matched_count": result.matched_count, "modified_count": result.modified_count},
            "context": context,
            "message": msg
        }

    @mongo_op(backoff=1, max_attempts=5)
    def update_many(self, query: dict, update: dict, upsert: bool = False, context: str = "", session: Optional[ClientSession] = None) -> dict:
        col = self._get_collection()
        result: UpdateResult = col.update_many(query, {"$set": update}, upsert=upsert, session=session)
        msg = f"[{context}] {result.modified_count} documentos modificados"
        self.logger.info(msg)
        return {
            "success": result.matched_count > 0,
            "data": {"matched_count": result.matched_count, "modified_count": result.modified_count},
            "context": context,
            "message": msg
        }

    # --------------------------
    # DELETE
    # --------------------------
    @mongo_op(backoff=1, max_attempts=5)
    def delete_one(self, query: dict, context: str = "", session: Optional[ClientSession] = None) -> dict:
        col = self._get_collection()
        result = col.delete_one(query, session=session)
        msg = f"[{context}] Documento eliminado" if result.deleted_count else f"[{context}] No se encontró documento para eliminar"
        self.logger.info(msg)
        return {
            "success": result.deleted_count > 0,
            "data": {"deleted_count": result.deleted_count},
            "context": context,
            "message": msg
        }

    # --------------------------
    # CREATE/UPDATE con log
    # --------------------------
    @mongo_op(backoff=1, max_attempts=5)
    def insert_with_log(self, document: dict, context: str = "", session=None) -> dict:
        return self.insert_one(document, context=context, session=session)

    @mongo_op(backoff=1, max_attempts=5)
    def update_with_log(self, query: dict, update: dict, upsert: bool = False, context: str = "", session=None) -> dict:
        return self.update_one(query, update, upsert=upsert, context=context, session=session)
