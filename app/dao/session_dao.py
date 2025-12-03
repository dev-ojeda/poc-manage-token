from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from bson import ObjectId
from functools import lru_cache

from app.core.base_dao import BaseDAO
from app.model.user_session_model import UserSessionModel
from app.logging_config import get_logger


class SessionDAO(BaseDAO):
    COLLECTION = "active_sessions"

    def __init__(self, db=None, logger=None):
        super().__init__(db=db, collection_name=self.COLLECTION)
        self.logger = logger or get_logger("SessionDAO")
        self.users_collection = "users"


    # ---------------------
    # Utilitarios
    # ---------------------
    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=timezone.utc)

    def _query_user(self, user_id: ObjectId, device_id: Optional[str] = None) -> Dict[str, Any]:
        query = {"user_id": user_id}
        if device_id:
            query["device_id"] = device_id
        return query

    # ---------------------
    # Caché LRU
    # ---------------------
    @lru_cache(maxsize=128)
    def _cached_get_active_session(self, user_id: str, device_id: Optional[str]) -> dict:
        projection = {
            "_id": 1, "user_id": 1, "device_id": 1, "ip_address": 1,
            "browser": 1, "os": 1, "login_at": 1, "last_refresh_at": 1,
            "refresh_token": 1, "is_revoked": 1, "reason": 1, "status": 1,
        }
        query = {"user_id": ObjectId(user_id)}
        if device_id:
            query["device_id"] = device_id
        return self.find_one(query, projection, context="Cached Active Session")

    @lru_cache(maxsize=256)
    def _cached_device_exists(self, device_id: str) -> bool:
        result = self.find_one({"device_id": device_id}, context="Cached Device ID")
        return bool(result.get("data"))

    def clear_cache(self):
        self._cached_get_active_session.cache_clear()
        self._cached_device_exists.cache_clear()

    # ---------------------
    # CRUD de sesiones
    # ---------------------
    def insert_session(self, session: UserSessionModel, *, context="Insert Active Session") -> dict:
        self.clear_cache()
        return self.insert_one(session.to_dict(), context=context)

    def get_active_session(self, user_id: ObjectId, device_id: Optional[str] = None, *, context="Get Active Session") -> dict:
        try:
            return self._cached_get_active_session(str(user_id), device_id)
        except Exception as e:
            self.logger.warning(f"[{context}] Cache miss o error: {e}")
            return self.find_one(self._query_user(user_id, device_id), context=context)

    def find_previous_session(self, username: str, device_id: str, *, context="Find Previous Session") -> dict:
        return self.find_one({"username": username, "device_id": device_id}, context=context)

    def device_id_exists(self, device_id: str, *, context="Check Device ID") -> bool:
        try:
            return self._cached_device_exists(device_id)
        except Exception as e:
            self.logger.warning(f"[{context}] Cache miss o error: {e}")
            result = self.find_one({"device_id": device_id}, context=context)
            return bool(result.get("data"))

    def revoke_session(self, user_id: ObjectId, reason: str, *, context="Revoke Session") -> dict:
        self.clear_cache()
        update_fields = {"$set": {"is_revoked": True, "revoked_at": self._now(), "status": "revoked", "reason": reason}}
        return self.update_one({"user_id": user_id}, update_fields, context=context)

    def update_session(self, user_id: ObjectId, token: str, reason: str, *, context="Update Session") -> dict:
        self.clear_cache()
        update_fields = {
            "$set": {
                "is_revoked": False,
                "revoked_at": None,
                "last_refresh_at": self._now(),
                "refresh_token": token,
                "status": "active",
                "reason": reason,
            }
        }
        return self.update_one({"user_id": user_id}, update_fields, context=context)

    def update_session_for_audit(self, user_id: ObjectId, ip_address: str, browser: str, reason: str, *, context="Audit Session Update") -> dict:
        self.clear_cache()
        update_fields = {"$set": {"ip_address": ip_address, "browser": browser, "last_refresh_at": self._now(), "reason": reason}}
        return self.update_one({"user_id": user_id}, update_fields, context=context)

    def has_active_session(self, user_id: ObjectId, *, context="Check Active Session") -> bool:
        filtro = {"user_id": user_id, "status": "active", "is_revoked": False}
        result = self.count(filtro, context=context)
        return result.get("data", {}).get("count", 0) > 0

    # ---------------------
    # Pipeline de sesiones activas con datos de usuario
    # ---------------------
    def get_active_sessions_with_user_data(self, filtro_status: Optional[str] = None, *, context="Get Active Sessions With User Data") -> dict:
        status_filter = filtro_status or {"$in": ["active", "revoked", "expired"]}
        match_stage = {"user_data.rol": {"$ne": "Admin"}, "revoked_at": None, "status": status_filter}

        pipeline = [
            {"$lookup": {"from": self.users_collection, "localField": "user_id", "foreignField": "_id", "as": "user_data"}},
            {"$unwind": "$user_data"},
            {"$match": match_stage},
            {"$project": {
                "_id": 1, "user_id": 1, "device_id": 1, "ip_address": 1, "browser": 1, "os": 1,
                "login_at": 1, "last_refresh_at": 1, "refresh_token": 1, "is_revoked": 1,
                "reason": 1, "status": 1, "user_data.username": 1, "user_data.email": 1, "user_data.rol": 1,
            }},
            {"$group": {"_id": None, "data": {"$push": "$$ROOT"}, "total_count": {"$sum": 1}}},
            {"$project": {"_id": 0, "data": 1, "total_count": 1}},
        ]
        return self.aggregate(pipeline, context=context)
