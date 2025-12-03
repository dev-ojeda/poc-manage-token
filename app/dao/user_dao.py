from typing import Optional, List, Dict
from bson import ObjectId
from datetime import datetime, timezone

from app.core.base_dao import BaseDAO
from app.model.user_model import UserModel


class UserDAO(BaseDAO):
    """DAO especializado para la colección 'users'."""

    COLLECTION = "users"

    def __init__(self, db=None, logger=None):
        super().__init__(db=db, collection_name=self.COLLECTION)
        self.logger = logger or self.logger.getChild("UserDAO")

    # ---------------------
    # Utilitarios
    # ---------------------
    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=timezone.utc)

    def _to_user_model(self, data: Optional[dict]) -> Optional[UserModel]:
        return UserModel.from_dict(data) if data else None

    # ---------------------
    # Métodos CRUD y consultas
    # ---------------------
    def find_by_id(self, user_id: str) -> Optional[UserModel]:
        res = self.find_one({"_id": ObjectId(user_id)}, context="Find User by ID")
        return self._to_user_model(res.get("data"))

    def find_by_username(self, username: str) -> Optional[UserModel]:
        projection = {
            "_id": 1, "username": 1, "password": 1, "email": 1,
            "rol": 1, "created_at": 1, "updated_at": 1,
            "failed_attempts": 1, "blocked_until": 1
        }
        res = self.find_one({"username": username}, projection=projection, context="Find by Username")
        return self._to_user_model(res.get("data"))

    def reset_login_attempts(self, user: UserModel) -> dict:
        query = {"username": user.username, "rol": user.rol}
        update = {"$set": {"failed_attempts": 0, "blocked_until": None}}
        return self.update_one(query, update, context="Reset Login Attempts")

    def count_documents_user(self, filtro: Optional[dict] = None) -> int:
        res = self.count(filtro or {}, context="Count Users")
        return res.get("data", {}).get("count", 0)

    def find_blocked(self) -> int:
        query = {"blocked_until": {"$gt": self._now()}}
        res = self.count(query, context="Count Blocked Users")
        return res.get("data", {}).get("count", 0)

    def get_all_users(self) -> List[Dict]:
        pipeline = [
            {"$match": {"rol": {"$ne": "Admin"}}},
            {"$project": {
                "_id": 0, "username": 1, "rol": 1, "created_at": 1,
                "updated_at": 1, "failed_attempts": 1, "blocked_until": 1
            }}
        ]
        res = self.aggregate(pipeline, context="Get All Users")
        return res.get("data", [])

    def create_user(self, user: UserModel) -> dict:
        return self.insert_one(user.to_dict(), context="Create User")
