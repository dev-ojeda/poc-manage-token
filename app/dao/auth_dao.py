import datetime
from datetime import timezone, timedelta
from bson import SON
from typing import Optional

from app.dao.base_dao import BaseDAO
from app.dao.session_dao import SessionDAO
from app.dao.audit_dao import AuditLogDAO
from app.utils.db_mongo import MongoDatabase


class AuthDAO(BaseDAO):
    def __init__(self, db: Optional[MongoDatabase] = None):
        super().__init__(db=db, collection_name="refresh_tokens")
        self.session_dao = SessionDAO(self.db)
        self.audit_dao = AuditLogDAO()

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(tz=timezone.utc)

    # ---------------------
    # Búsquedas y validaciones
    # ---------------------
    def get_active_token_by_user_and_device(self, username: str, device_id=None):
        match_filter = {"username": username, "revoked_at": None, "expires_at": {"$gt": self._now()}}
        if device_id: match_filter["device_id"] = device_id
        pipeline = [{"$match": match_filter}, {"$sort": SON([("created_at", -1)])}, {"$limit": 1}]
        result = self.aggregate(pipeline)
        data = result.get("data", [])
        return {"success": True, "data": data[0] if data else None}

    def get_active_token_by_username(self, username: str, *, context: str = "") -> dict:
        match_filter = {
            "username": username,
            "revoked_at": None,
            "expires_at": {"$gt": self._now()}
        }

        pipeline = [
            {"$match": match_filter},
            {"$sort": SON([("created_at", -1)])},
            {"$limit": 1},
            {"$project": {
                "_id": 1,
                "username": 1,
                "device_id": 1,
                "jti": 1,
                "refresh_token": 1,
                "created_at": 1,
                "expires_at": 1,
                "revoked_at": 1,
                "used_at": 1
            }}
        ]

        result = self.aggregate(pipeline, context=context)
        data = result.get("data", [])
        return {"success": True, "data": data[0] if data else None, "context": context or "Active Token by Username"}

    def get_refresh_token(self, refresh_token: str, *, context: str = "") -> dict:
        query = {"refresh_token": refresh_token}
        projection = {"_id": 0, "revoked_at": 1, "refresh_attempts": 1}
        return self.find_one(query=query, projection=projection, context=context or "Get Refresh Token")

    def is_valid_refresh_token(self, refresh_token: str, device_id: str, *, context: str = "") -> dict:
        query = {
            "refresh_token": refresh_token,
            "device_id": device_id,
            "expires_at": {"$gt": self._now()}
        }
        token = self.find_one(query=query, context=context).get("data")
        valid = bool(token) and not token.get("revoked_at")
        return {"success": True, "data": valid, "context": context or "Validate Refresh Token"}

    def is_token_in_use(self, username: str, *, context: str = "") -> dict:
        query = {"username": username, "used_at": {"$ne": None}}
        projection = {"_id": 1, "username": 1, "device_id": 1, "refresh_token": 1, "jti": 1, "expires_at": 1}
        result = self.find_one(query=query, projection=projection, context=context)
        return {"success": True, "data": result["data"], "context": context or "Check Token Usage"}

    # ---------------------
    # Revocación y actualización de tokens
    # ---------------------
    def revoke_tokens(self, query_filter: dict, context: str):
        update = {"$set": {"revoked_at": self._now()}}
        return self.update_many(query_filter, update, context=context)

    def revoke_old_token(self, **kwargs) -> dict:
        now = self._now()
        query = {k: kwargs[k] for k in ("username", "refresh_token", "jti")}
        update = {"$set": {"revoked_at": now, "used_at": now}}
        return self.update_one(query=query, update=update, upsert=kwargs.get("upsert", False), context="Revoke Old Tokens")


    def revoke_all_tokens_for_user(self, username: str, *, context: str = "") -> dict:
        return self.revoke_tokens({"username": username, "revoked_at": None}, context=context or "Revoke All Tokens")

    def revoke_token_by_jti(self, jti: str, *, context: str = "") -> dict:
        return self.revoke_tokens({"jti": jti, "revoked_at": None}, context=context or "Revoke Token by JTI")

    def revoke_token_by_device_id(self, device_id: str, *, context: str = "") -> dict:
        return self.revoke_tokens({"device_id": device_id}, context=context or "Revoke Token by Device ID")

    def mark_token_as_used(self, **kwargs) -> dict:
        now = self._now()
        query = {k: kwargs[k] for k in ("username", "device_id", "jti", "refresh_token")}
        update = {"$set": {"revoked_at": now, "used_at": now}}
        return self.update_one(query=query, update=update, upsert=kwargs.get("upsert", False), context="Mark Token Used")

    # def update_refresh_token(self, **kwargs):
    #     now = self._now()
    #     query = {"username": kwargs["username"], "device_id": kwargs["device_id"]}
    #     update = {"$set": {"jti": kwargs["jti"], "refresh_token": kwargs["refresh_token"], "update_at": now,
    #                     "expires_at": now + timedelta(minutes=4), "revoked_at": None,
    #                     "refresh_attempts": kwargs["refresh_attempts"], "browser": kwargs["browser"],
    #                     "os": kwargs["os"], "ip_address": kwargs["ip_address"]},
    #             "$setOnInsert": {"username": kwargs["username"], "device_id": kwargs["device_id"], "created_at": now,
    #                             "used_at": now}}
    #     return self.update_with_log(query, update, upsert=True, context="Upsert Refresh Token")

    
    def upsert_refresh_token(self, **kwargs):
        previous = self.session_dao.find_previous_session(username=kwargs["username"], device_id=kwargs["device_id"])
        if previous.get("data"):
            audit_result = self.audit_dao.insert_event_audit(previous_session=previous["data"], **kwargs)
            if not audit_result.get("success"):
                return audit_result
        now = self._now()
        query = {"username": kwargs["username"], "device_id": kwargs["device_id"]}
        update = {"$set": {
            "jti": kwargs["jti"], "refresh_token": kwargs["refresh_token"],
            "update_at": now, "expires_at": now + timedelta(minutes=4), "revoked_at": None,
            "refresh_attempts": kwargs["refresh_attempts"], "browser": kwargs["user_agent"]["browser"],
            "os": kwargs["user_agent"]["os"], "ip_address": kwargs["ip_address"]
        }, "$setOnInsert": {"username": kwargs["username"], "device_id": kwargs["device_id"], "created_at": now,"used_at": now}}
        return self.update_one(query, update, upsert=True, context="Upsert Refresh Token")
