from dataclasses import asdict, dataclass
import datetime
from datetime import timezone
from typing import Optional, Dict, Any

from bson import ObjectId

@dataclass
class ItemModel:
    _id: Optional[str] = None
    user_id: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    item_id:  Optional[ObjectId | str] = None
    @classmethod
    def from_dict(cls, data: dict):
        user_id = data.get("user_id") or data.get("usuario_id")
        item_id = data.get("_id") or data.get("item_id")
        return cls(
            item_id=item_id,
            user_id=user_id,
            name=data.get("name", ""),
            description=data.get("description"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
# class ItemModel:
#     def __init__(
#         self,
#         user_id: ObjectId | str,
#         name: str,
#         description: Optional[str] = None,
#         created_at: Optional[datetime.datetime] = None,
#         updated_at: Optional[datetime.datetime] = None,
#         item_id:  Optional[ObjectId | str] = None
#     ):
#         self._item_id =  self._ensure_objectid(item_id) if item_id is not None else None
#         self._user_id = self._ensure_objectid(user_id) if user_id is not None else None
#         self._name = name
#         self._description = description
#         self._created_at = created_at
#         self._updated_at = updated_at


    
#     # -------------------
#     # Helper static
#     # -------------------
#     @staticmethod
#     def _ensure_objectid(value: Any) -> ObjectId:
#         if isinstance(value, ObjectId):
#             return value
#         if value is None:
#             raise ValueError("ObjectId requerido, se recibió None")
#         try:
#             return ObjectId(str(value))
#         except Exception as e:
#             raise ValueError(f"Valor inválido para ObjectId: {value}") from e


#     @property
#     def item_id(self) -> Optional[ObjectId]:
#         return self._item_id

#     @item_id.setter
#     def item_id(self, v: ObjectId | str | None):
#         self._item_id = self._ensure_objectid(v) if v is not None else None
#     # ---- user_id ----
#     @property
#     def user_id(self) -> ObjectId:
#         return self._user_id

#     @user_id.setter
#     def user_id(self, v: ObjectId | str):
#         self._user_id = self._ensure_objectid(v)

#     # ---- name ----
#     @property
#     def name(self) -> str:
#         return self._name

#     @name.setter
#     def name(self, value: str):
#         if not value:
#             raise ValueError("El nombre no puede estar vacío")
#         self._name = value

#     # ---- description ----
#     @property
#     def description(self) -> Optional[str]:
#         return self._description

#     @description.setter
#     def description(self, value: Optional[str]):
#         if value is not None and not isinstance(value, str):
#             raise ValueError("La descripción debe ser string o None")
#         self._description = value

#     # ---- created_at ----
#     @property
#     def created_at(self) -> Optional[datetime.datetime]:
#         return self._created_at

#     @created_at.setter
#     def created_at(self, value: Optional[datetime.datetime]):
#         if not isinstance(value, datetime.datetime):
#             raise ValueError("created_at debe ser datetime")
#         self._created_at = value

#     # ---- updated_at ----
#     @property
#     def updated_at(self) -> Optional[datetime.datetime]:
#         return self._updated_at

#     @updated_at.setter
#     def updated_at(self, value: Optional[datetime.datetime]):
#         if not isinstance(value, datetime.datetime):
#             raise ValueError("updated_at debe ser datetime")
#         self._updated_at = value

#     # ---- Mongo Helpers ----
#     def to_dict(self) -> Dict[str, Any]:
#         """Convierte la instancia en un dict para MongoDB"""
#         return {
#             "user_id": self.user_id,
#             "name": self.name,
#             "description": self.description,
#             "created_at": self.created_at,
#             "updated_at": self.updated_at
#         }

#     @classmethod
#     def from_dict(cls, data: Dict) -> "ItemModel":
#         """Crea un objeto ItemModel desde un dict de MongoDB"""
#         user_id = data.get("user_id") or data.get("usuario_id")
#         item_id = data.get("_id") or data.get("item_id")
#         return cls(
#             item_id=item_id,
#             user_id=user_id,
#             name=data.get("name"),
#             description=data.get("description"),
#             created_at=data.get("created_at", datetime.datetime.now(tz=timezone.utc)),
#             updated_at=data.get("updated_at", datetime.datetime.now(tz=timezone.utc))
#         )