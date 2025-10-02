#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from datetime import timezone
from typing import Optional
from bson import ObjectId
from pymongo.errors import PyMongoError

from app.dao.base_dao import BaseDAO
from app.model.user_model import UserModel
from icecream import ic


class UserDAO(BaseDAO):
    def __init__(self, db=None):
        super().__init__(db=db, collection_name="users")

    # ---------------------
    # Métodos específicos
    # ---------------------
    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(tz=timezone.utc)

    def find_by_id(self, user_id: str, *, context="") -> UserModel | None:
        try:
            result = self.find_one({"_id": ObjectId(user_id)}, context=context)
            return UserModel.from_dict(result.get("data")) if result.get("data") else None
        except PyMongoError:
            return None

    def reset_login_attempts(self, user: UserModel) -> dict:
        return self.update_one(
            {"username": user.username, "rol": user.rol},
            {"$set": {"failed_attempts": 0, "blocked_until": None}},
            upsert=True,
            context="Reset Intentos"
        )

    def find_by_username(self, username: str, *, context="") -> UserModel | None:
        try:
            query = {"username": username}
            projection = {
                "_id": 1,
                "username": 1,
                "password": 1,
                "email": 1,
                "rol": 1,
                "created_at": 1,
                "updated_at": 1,
                "failed_attempts": 1,
                "blocked_until": 1
            }
            result = self.find_one(query, projection, context=context)
            return UserModel.from_dict(result.get("data")) if result.get("data") else None
        except PyMongoError:
            return None

    def count_documents_user(self, filtro: Optional[dict] = None, *, context: str = "") -> int:
        """Cuenta documentos de usuarios (no recursivo)"""
        try:
            result = super().count_documents(filtro or {}, context=context)
            return result.get("count", 0)
        except PyMongoError as e:
            ic(f"❌ Error en count_documents_user: {e}")
            return 0

    def find_blocked(self, *, context: str = "") -> int:
        """Cuenta usuarios bloqueados"""
        query = {"blocked_until": {"$gt": self._now()}}
        try:
            result = super().count_documents(query, context=context)
            return result.get("count", 0)
        except PyMongoError as e:
            ic(f"❌ Error en find_blocked: {e}")
            return 0

    def get_all_users(self, *, context="") -> list[dict]:
        pipeline = [
            {"$match": {"rol": {"$ne": "Admin"}}},
            {"$project": {"_id": 0, "username": 1, "rol": 1, "created_at": 1, "updated_at": 1, "failed_attempts": 1, "blocked_until": 1}}
        ]
        result = self.aggregate(pipeline, context=context)
        return result.get("data", [])

    def create_user(self, user: UserModel, *, context: str = "") -> dict:
        """
        Inserta un nuevo usuario a partir de un modelo
        """
        return self.insert_one(user.to_dict(), context=context)
