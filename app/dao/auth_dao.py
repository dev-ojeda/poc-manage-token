from datetime import datetime, timezone

from bson import SON

from app.utils.db_mongo import MongoDatabase


class AuthDao:
    def __init__(self, db=None):
        self.db = db or MongoDatabase()
        # Si es mongomock o un Database de pymongo, exponemos la colección
        if hasattr(self.db, "__getitem__"):
            self.collection = self.db["refresh_tokens"]
        else:
            self.collection = None
        self.refresh_tokens = "refresh_tokens"

    def get_active_token_by_user(self, username: str, device_id: str):
        now = datetime.now(timezone.utc)
        match_filter = {
            "username": username,
            "revoked": False,
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

    def revoke_token_by_device_id(self, device_id):
        query = {"device_id": device_id, "revoked": False}
        update = {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}}
        if self.collection:
            result = self.collection.update_many(query, update)
        else:
            result = self.db.update_many(collection=self.refresh_tokens, query=query, update=update)
        return result.modified_count

    def mark_token_as_used(self, username: str, device_id: str, jti: str, refresh_token: str, created_at: None, expires_at: None, upsert: bool):
        query = {
            "username": username, 
            "device_id": device_id, 
            "jti": jti,
            "revoked": False,
            "refresh_token": refresh_token,
            "created_at": created_at,
            "expires_at": expires_at
        }

        update = {
            "$set": {
                "used_at": datetime.now(timezone.utc)
            }
        }
        if self.collection:
            result = self.collection.update_one(query, update, upsert=upsert)
        else:
            result = self.db.update_with_log(collection=self.refresh_tokens, query=query, update=update, upsert=True)
        return result.modified_count
           