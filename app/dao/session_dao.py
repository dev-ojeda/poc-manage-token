
from datetime import datetime, timezone

from bson import ObjectId
from utils.db_mongo import MongoDatabase
from model.user_session import UserSession

class SessionDAO:
    def __init__(self):
        self.db = MongoDatabase()
        self.active_sessions = "active_sessions"
        self.users = "users"

    def insert_session(self, session: UserSession) -> dict:
        return self.db.insert_with_log(self.active_sessions,session.to_dict(),context="Insertar sesión activa")
    def get_active_session(self, user_id: ObjectId, device_id:str) -> dict:
        query={
            "user_id": user_id,
            "device_id": device_id
         }
        projection = {
            "_id": 1,
            "user_id": 1,
            "ip_address": 1,
            "user_agent": 1,
            "device_id": 1,
            "login_at": 1,
            "last_refresh_at": 1,
            "refresh_token": 1,
            "is_revoked": 1,
            "reason": 1
        }
        return self.db.find_one(self.active_sessions,query=query,projection=projection)
    def revoked_session(self, user_id:ObjectId, reason: str):
        query={"user_id": user_id}
        update_fields = {
            "$set": {
                "is_revoked": True,
                "revoked_at": datetime.now(timezone.utc),
                "status": "revoked",
                "reason": reason
            }
        }
        return self.db.update_with_log(self.active_sessions,query=query,update=update_fields,upsert=False,context="Revocar Session")
    def update_session(self, user_id:ObjectId, reason: str):
        query={"user_id": user_id}
        update_fields = {
            "$set": {
                "is_revoked": False,
                "revoked_at": None,
                "last_refresh_at": self.update_datetime_format_iso(self.get_datetime_now()),
                "status": "active",
                "reason": reason
            }
        }
        return self.db.update_with_log(self.active_sessions,query=query,update=update_fields,upsert=False,context="Session Cerrada")

    def get_active_sessions_with_user_data(self, filtro_status: str = None):
        match_stage = {
            "user_data.rol": {"$ne": "Admin"},
            "revoked_at": None,
            "is_revoked": False,
        }
         # Si se pasa un estado específico, lo agregamos al filtro
        if filtro_status:
            match_stage["status"] = filtro_status
        else:
            match_stage["status"] = {"$in": ["active", "revoked", "expired"]}
        
        pipeline = [
            {
                "$lookup": {
                    "from": self.users,                 # Colección con la que haces join
                    "localField": "user_id",         # Campo en active_sessions
                    "foreignField": "_id",           # Campo en users
                    "as": "user_data"                # Nombre del campo resultante
                }
            },
            {
                "$unwind": "$user_data"  # Aplana el array de user_data (siempre que haya match)
            },
            {
                "$match": match_stage
            },
            {
                "$project": {
                    "_id": 1,
                    "user_id": 1,
                    "ip_address": 1,
                    "browser": 1,
                    "os": 1,
                    "device_id": 1,
                    "login_at": 1,
                    "last_refresh_at": 1,
                    "refresh_token": 1,
                    "is_revoked": 1,
                    "reason": 1,
                    "status": 1,
                    "user_data.username": 1,
                    "user_data.email": 1,
                    "user_data.rol": 1
                }
            }
        ]
        return list(self.db.aggregate(self.active_sessions,pipeline))
    def get_datetime_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def update_datetime_format_iso(self, fecha: datetime) -> datetime:
        return fecha.fromisoformat(fecha.isoformat())