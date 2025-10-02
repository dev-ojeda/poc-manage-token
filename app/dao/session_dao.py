from typing import Optional, Dict, List, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.errors import PyMongoError

from app.model.user_session_model import UserSessionModel
from app.dao.base_dao import BaseDAO


class SessionDAO(BaseDAO):
    def __init__(self, db=None):
        super().__init__(db=db, collection_name="active_sessions")
        self.users_collection = "users"

    def _now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    # ---------------------
    # CRUD de sesiones
    # ---------------------
    def insert_session(self, session: UserSessionModel, *, context="Insertar sesión activa") -> dict:
        return self.insert_one(session.to_dict(), context=context)

    def get_active_session(self, user_id: ObjectId, device_id: Optional[str] = None, *, context="Get Active Session") -> dict:
        query = {"user_id": user_id}
        if device_id:
            query["device_id"] = device_id
        projection = {
            "_id": 1, "user_id": 1, "device_id": 1, "ip_address": 1,
            "browser": 1, "os": 1, "login_at": 1, "last_refresh_at": 1,
            "refresh_token": 1, "is_revoked": 1, "reason": 1
        }
        return self.find_one(query=query, projection=projection, context=context)

    def find_previous_session(self, username: str, device_id: str, *, context="Find Previous Session") -> dict:
        query = {"username": username, "device_id": device_id}
        return self.find_one(query=query, context=context)

    def device_id_exists(self, device_id: str, *, context="Check Device ID") -> bool:
        query = {"device_id": device_id}
        projection = {"device_id": 1}
        result = self.find_one(query=query, projection=projection, context=context)
        return bool(result.get("data"))

    def revoke_session(self, user_id: ObjectId, reason: str, *, context="Revoke Session") -> dict:
        query = {"user_id": user_id}
        update_fields = {"$set": {"is_revoked": True, "revoked_at": self._now(), "status": "revoked", "reason": reason}}
        return self.update_with_log(query=query, update=update_fields, upsert=False, context=context)

    def update_session(self, user_id: ObjectId, token: str, reason: str, *, context="Update Session") -> dict:
        query = {"user_id": user_id}
        update_fields = {
            "$set": {
                "is_revoked": False,
                "revoked_at": None,
                "last_refresh_at": self._now(),
                "refresh_token": token,
                "status": "active",
                "reason": reason
            }
        }
        return self.update_with_log(query=query, update=update_fields, upsert=False, context=context)

    def update_session_for_audit(self, user_id: ObjectId, ip_address: str, browser: str, reason: str, *, context="Update Session Audit") -> dict:
        query = {"user_id": user_id}
        update_fields = {"$set": {"ip_address": ip_address, "browser": browser, "last_refresh_at": self._now(), "reason": reason}}
        return self.update_with_log(query=query, update=update_fields, upsert=False, context=context)

    def has_active_session(self, user_id: ObjectId, *, context="Check Active Session") -> bool:
        filtro = {"user_id": user_id, "status": "active", "is_revoked": False}
        count_result = self.count_documents(filtro, context=context)
        return count_result.get("count", 0) > 0

    # ---------------------
    # Consultas avanzadas
    # ---------------------
    def get_active_sessions_with_user_data(self, filtro_status: Optional[str] = None, *, context="Get Active Sessions With User Data") -> dict:
        match_stage: Dict[str, Any] = {"user_data.rol": {"$ne": "Admin"}, "revoked_at": None}
        match_stage["status"] = filtro_status if filtro_status else {"$in": ["active", "revoked", "expired"]}

        pipeline = [
            {"$lookup": {"from": self.users_collection, "localField": "user_id", "foreignField": "_id", "as": "user_data"}},
            {"$unwind": "$user_data"},
            {"$match": match_stage},
            {"$project": {
                "_id": 1, "user_id": 1, "device_id": 1, "ip_address": 1,
                "browser": 1, "os": 1, "login_at": 1, "last_refresh_at": 1,
                "refresh_token": 1, "is_revoked": 1, "reason": 1, "status": 1,
                "user_data.username": 1, "user_data.email": 1, "user_data.rol": 1
            }}
        ]
        return self.aggregate(pipeline)
