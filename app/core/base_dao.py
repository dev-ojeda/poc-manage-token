# app/core/base_dao.py
from typing import Optional, Dict, Any, List
from app.utils.mongo_op import mongo_op

class BaseDAO:
    """
    DAO base: encapsula operaciones CRUD con MongoDB usando mongo_op resiliente.
    Cada colección es automáticamente segura frente a desconexiones.
    """

    def __init__(self, collection_name: str, db=None):
        if not collection_name:
            raise ValueError("collection_name es obligatorio para inicializar BaseDAO")
        self.collection_name = collection_name
        self.db_instance = db or mongo_op.db_instance
        self.collection = self.db_instance.db[collection_name]
        self.logger = mongo_op.logger

    # -------------------------
    # CRUD genérico
    # -------------------------
    def insert_one(self, doc: Dict[str, Any], *, context: str = "insert_one") -> dict:
        return mongo_op.insert_one(self.collection, doc, context=context)

    def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None, *, context: str = "find_one") -> dict:
        return mongo_op.find_one(self.collection, query, projection, context=context)

    def find_many(self, query: Dict[str, Any], projection: Optional[Dict[str, int]] = None, *, context: str = "find_many") -> dict:
        return mongo_op.find_many(self.collection, query, projection, context=context)

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any], *, context: str = "update_one") -> dict:
        return mongo_op.update_one(self.collection, query, update, context=context)

    def delete_one(self, query: Dict[str, Any], *, context: str = "delete_one") -> dict:
        return mongo_op.delete_one(self.collection, query, context=context)

    def replace_one(self, query: Dict[str, Any], new_doc: Dict[str, Any], *, context: str = "replace_one") -> dict:
        return mongo_op.replace_one(self.collection, query, new_doc, context=context)

    def aggregate(self, pipeline: List[Dict[str, Any]], *, context: str = "aggregate") -> dict:
        return mongo_op.aggregate(self.collection, pipeline, context=context)

    def count(self, query: Dict[str, Any], *, context: str = "count") -> dict:
        return mongo_op.count(self.collection, query, context=context)

    def upsert_token(self,**kwargs) -> dict:
        return mongo_op.upsert_refresh_token(self.collection,**kwargs)