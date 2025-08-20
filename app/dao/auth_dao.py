from datetime import datetime, timedelta, timezone

from bson import SON
from icecream import ic

from app.dao.audit_dao import AuditLogDAO
from app.dao.session_dao import SessionDAO
from app.utils.db_mongo import MongoDatabase


class AuthDao:
    def __init__(self, db=None):
        self.db = db or MongoDatabase()
        self.session_dao = SessionDAO()
        self.audit_dao = AuditLogDAO()
        # Si es mongomock o un Database de pymongo, exponemos la colección
        if hasattr(self.db, "__getitem__"):
            self.collection = self.db["refresh_tokens"]
        else:
            self.collection = None
        self.refresh_tokens = "refresh_tokens"
  

    def get_active_token_by_user_and_device(self, username: str, device_id: str):
        now = datetime.now(timezone.utc)
        match_filter = {
            "username": username,
            "revoked_at": None,
            "expires_at": {"$gt": now}
        }
        if device_id:
            match_filter["device_id"] = device_id

        pipeline = [
            {"$match": match_filter},
            {"$sort": SON([("created_at", -1)])},
            {"$limit": 1}
        ]

        if self.collection:  # MongoMock o pymongo puro
            result = list(self.collection.aggregate(pipeline))
        else:  # MongoDatabase wrapper
            result = list(self.db.aggregate(collection=self.refresh_tokens, pipeline=pipeline))
        return result[0] if result else None

    def get_active_token_by_username(self, username: str):
        now = datetime.now(timezone.utc)
        match_filter = {
            "username": username,
            "revoked": False,
            "expires_at": {"$gt": now}
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
                "revoked": 1,
                "used_at": 1   # 👉 incluimos el campo
            }}
        ]

        if self.collection:  # MongoMock o pymongo puro
            result = list(self.collection.aggregate(pipeline))
        else:  # MongoDatabase wrapper
            result = list(self.db.aggregate(collection=self.refresh_tokens, pipeline=pipeline))
            ic(f"[ACTIVE_TOKEN_USER]: {result}")
        return result[0] if result else None

    def is_token_in_use(self, username: str) -> dict:
        """
        Verifica si algún token de este usuario ya ha sido usado.
        Devuelve True si existe al menos un token con 'used_at' definido.
        """
        query = {
            "username": username,
            "used_at": {"$ne": None}  # distinto de None => ya usado
        }
        projection = {"_id": 1, "username": 1, "device_id": 1, "refresh_token": 1, "jti": 1}
        token_doc = self.db.find_one(self.refresh_tokens,query=query,projection=projection)
        return token_doc if token_doc else None

    def revoke_all_tokens_for_user(self, username):
        query = {"username": username, "revoked": False}
        update = {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}}
        if self.collection:
            result = self.collection.update_many(query, update)
        else:
            result = self.db.update_many(collection=self.refresh_tokens, query=query, update=update)
        return result.modified_count

    def revoke_token_by_jti(self, jti):
        query = {"jti": jti, "revoked": False}
        update = {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}}
        if self.collection:
            result = self.collection.update_many(query, update)
        else:
            result = self.db.update_with_log(
                collection=self.refresh_tokens,
                query=query,
                update=update,
                upsert=True,
                context="Revocar token por JTI"
            )
        return result.modified_count

    def revoke_token_by_device_id(self, device_id) -> int | None:
        query = {"device_id": device_id}
        update = {"$set": {"revoked_at": datetime.fromisoformat(datetime.now(timezone.utc).isoformat())}}
        if self.collection:
            result = self.collection.update_many(query, update)
        else:
            result = self.db.update_many(collection=self.refresh_tokens, query=query, update=update)
        return result

    def mark_token_as_used(self, username: str, device_id: str, jti: str, refresh_token: str, created_at: None, expires_at: None, refresh_attempts: int, browser: str, os: str, ip_address:str, upsert: bool):
        query = {
            "username": username, 
            "device_id": device_id, 
            "jti": jti,
            "refresh_token": refresh_token,
            "created_at": created_at,
            "expires_at": expires_at,
            "refresh_attempts": refresh_attempts,
            "browser": browser,
            "os": os,
            "ip_address": ip_address
        }

        update = {
            "$set": {
                "revoked_at": datetime.fromisoformat(datetime.now(timezone.utc).isoformat()),
                "used_at": datetime.fromisoformat(datetime.now(timezone.utc).isoformat())
            }
        }
        if self.collection:
            result = self.collection.update_one(query, update, upsert=upsert)
        else:
            result = self.db.update_with_log(collection=self.refresh_tokens, query=query, update=update, upsert=upsert, context="Marcar Token Usuado y Revocado")
        return result.modified_count
           
    def revoke_refresh_token(self, username: str, device_id: str, refresh_token: str) -> dict:
        revoked_at = datetime.fromisoformat(datetime.now(timezone.utc).isoformat())
        return self.db.update_with_log(self.refresh_tokens,
            {"username": username, "device_id": device_id, "refresh_token": refresh_token, "revoked_at": None},
            {
                "$set": 
                {
                    "revoked_at": revoked_at
                }
            },upsert=False,context="Revocar Refresh Token"
        )

    def update_refresh_token(self, **kwargs) -> dict:
        expires_at =  datetime.fromisoformat(datetime.now(timezone.utc).isoformat()) + timedelta(seconds=360)
        created_at =  datetime.fromisoformat(datetime.now(timezone.utc).isoformat())
        update_at =  datetime.fromisoformat(datetime.now(timezone.utc).isoformat())
        used_at =  datetime.fromisoformat(datetime.now(timezone.utc).isoformat())
        return self.db.update_with_log(self.refresh_tokens,
             {"username":  kwargs["username"], "device_id":  kwargs["device_id"]},
             {
                 "$set": {
                     "jti": kwargs["jti"],
                     "refresh_token": kwargs["refresh_token"],
                     "update_at": update_at,
                     "expires_at": expires_at,
                     "revoked_at": None,
                     "refresh_attempts": kwargs["refresh_attempts"],
                     "browser": kwargs["browser"],
                     "os": kwargs["os"],
                     "ip_address": kwargs["ip_address"]
                 },
                 "$setOnInsert": {
                     "username": kwargs["username"],
                     "device_id": kwargs["device_id"],
                     "created_at": created_at,
                     "used_at": used_at
                 }
             },
             upsert=True,
             context="Upsert Refresh Token"
         )

    def upsert_refresh_token(self, **kwargs) -> dict:
    
        device_id = kwargs["device_id"]
        username = kwargs["username"]
        # Buscar sesión previa con mismo usuario + dispositivo
        previous_session = self.session_dao.find_previous_session(username=username,device_id=device_id)

        ic(f"[AUDITORÍA] SESSION PREVIOUS: {previous_session}")

        if previous_session is not None:
            event_audit = self.audit_dao.insert_event_audit(previous_session=previous_session, **kwargs)
            if not event_audit.get("success"):
                return event_audit     
        return self.update_refresh_token(**kwargs)