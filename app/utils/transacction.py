# refresh_token_service.py
from datetime import datetime
from typing import Dict
from app.utils.mongo_op import mongo_op
from app.extensions import db_mongo
from bson import ObjectId

class RefreshTokenService:
    """
    Servicio para manejar tokens refresh con upsert seguro y auditoría opcional.
    """

    COLLECTION_NAME = "refresh_tokens"

    def __init__(self, db):
        self.db = db
        self.collection = db[self.COLLECTION_NAME]

    def upsert_refresh_token(
        self,
        username: str,
        device_id: str,
        jti: str,
        refresh_token: str,
        refresh_attempts: int,
        user_agent: Dict[str, str],
        ip_address: str
    ) -> Dict:
        """
        Inserta o actualiza un refresh token para un usuario y dispositivo.
        """
        return mongo_op.upsert_refresh_token(
            collection=self.collection,
            username=username,
            device_id=device_id,
            jti=jti,
            refresh_token=refresh_token,
            refresh_attempts=refresh_attempts,
            user_agent=user_agent,
            ip_address=ip_address,
            context="RefreshToken Upsert"
        )

    def get_active_token_by_username(self, username: str) -> Dict:
        """
        Devuelve el refresh token activo más reciente de un usuario.
        """
        from bson.son import SON
        pipeline = [
            {"$match": {"username": username, "revoked_at": None, "expires_at": {"$gt": datetime.utcnow()}}},
            {"$sort": SON([("created_at", -1)])},
            {"$limit": 1},
            {"$project": {
                "_id": 1, "username": 1, "device_id": 1, "jti": 1,
                "refresh_token": 1, "created_at": 1, "expires_at": 1,
                "revoked_at": 1, "used_at": 1
            }}
        ]
        return mongo_op.aggregate(self.collection, pipeline, context="Get Active Token by Username")


service = RefreshTokenService(db=db_mongo.db)

# Upsert token
res = service.upsert_refresh_token(
    username="neo",
    device_id="device-001",
    jti="abc123xyz",
    refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    refresh_attempts=0,
    user_agent={"browser": "Chrome", "os": "Windows", "raw": "Mozilla/5.0..."},
    ip_address="192.168.0.1"
)
print(res)

# Consultar token activo
active_token = service.get_active_token_by_username("neo")
print(active_token)