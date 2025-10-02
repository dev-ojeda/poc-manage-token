import datetime
from datetime import timezone
from typing import Optional
from bson import ObjectId
import logging


from app.dao.base_dao import BaseDAO
from app.model.item_model import ItemModel
from app.utils.db_mongo import MongoDatabase

db = MongoDatabase()
class ItemDAO(BaseDAO):
    def __init__(self, db: Optional[MongoDatabase] = None):
        super().__init__(db=db, collection_name="items")
        self.logger = logging.getLogger(f"DAO.{self.__class__.__name__}")
    # -------------------------------
    # Crear item
    def create(self, item_model: ItemModel, session=None) -> dict:
        """Inserta un nuevo item en la colección y devuelve un dict consistente"""
        try:
            user_oid = ObjectId(item_model.user_id)
        except Exception as e:
            msg = f"user_id inválido: {e}"
            self.logger.warning(f"[Insert Item] {msg}")
            return {"success": False, "data": None, "message": msg, "context": "Insert Item"}

        now = datetime.datetime.now(tz=timezone.utc)
        document = {
            "user_id": user_oid,
            "name": item_model.name,
            "description": item_model.description,
            "created_at": now,
            "updated_at": now
        }

        try:
            result = self.insert_one(document=document, context="Insert Item", session=session)
            if result.get("acknowledged"):
                self.logger.info(f"[Insert Item] Documento insertado: {result['inserted_id']}")
                data = {"inserted_id": str(result["inserted_id"])}
            else:
                self.logger.warning("[Insert Item] Inserción no confirmada")
                data = None
            return {"success": True, "data": data, "context": "Insert Item"}
        except Exception as e:
            msg = f"Error al insertar item: {e}"
            self.logger.error(f"[Insert Item] {msg}")
            return {"success": False, "data": None, "message": msg, "context": "Insert Item"}

    # -------------------------------
    # Obtener items de un usuario
    # -------------------------------
     # -------------------------------
    # Obtener items de un usuario
    # -------------------------------
    def get_all_by_user(self, user_id: str) -> dict:
        """Devuelve todos los items asociados a un usuario en formato consistente"""
        try:
            user_oid = ObjectId(user_id)
        except Exception as e:
            msg = f"user_id inválido: {e}"
            self.logger.warning(f"[Get Items By User] {msg}")
            return {"success": False, "data": [], "message": msg, "context": "Get Items By User"}

         # Pipeline base
        # pipeline = [
        #     {"$match": {"user_id": user_oid}},
        #     {"$project": {
        #         "item_id": "$_id",
        #         "user_id": "$user_id",
        #         "name": "$name",
        #         "description": "$description",
        #         "created": "$created_at",
        #         "updated": "$updated_at"
        #     }}
        # ]
   
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
                "item_id": "$_id",
                "user_id": "$user_id",
                "name": "$name",
                "description": "$description",
                "created": "$created_at",
                "updated": "$updated_at"
                }
            }
        ]
       
        try:
            result = self.aggregate(pipeline=pipeline)
            items = [ItemModel.from_dict(doc) for doc in result["data"]]
            # Si quieres salida lista para JSON:
            items = [item.to_dict() for item in items]
        except Exception as e:
            msg = f"Error al obtener items: {e}"
            self.logger.error(f"[Get Items By User] {msg}")
            return {"success": False, "data": [], "message": msg, "context": "Get Items By User"}

        self.logger.info(f"[Get Items By User] {len(items)} items encontrados para user_id={user_id}")
        return {"success": True, "data": items, "context": "Get Items By User"}
