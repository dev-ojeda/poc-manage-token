#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from pymongo.errors import PyMongoError
from app.model.user import User
from icecream import ic

from app.utils.db_mongo import MongoDatabase


class UserDAO:
    def __init__(self):
        self.db = MongoDatabase()
        self.users = "users"
        self.active_sessions = "active_sessions"

    def find_by_id(self, user_id: str) -> User | None:
        query = {"_id": ObjectId(user_id)}
        projection = {
            "_id": 0,
            "username": 1,
            "password": 1,
            "email": 1,
            "rol": 1,
            "created_at": 1,
            "updated_at": 1,
            "failed_attempts": 1,
            "blocked_until": 1
        }
        return self.find_one(query=query, projection=projection) 
   
    def find_by_username(self, username: str) -> Optional[User]:
             
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

        return self.find_one(query=query, projection=projection)  # Podés incluir `projection` si extendés el método
    def find_one(self, query: Optional[dict] = None, projection: Optional[dict] = None) -> User | None:
        query = query or {}
        projection = projection or {}
        try:
            result = self.db.find_one(collection=self.users, query=query, projection=projection)
            ic(f"[FIND ONE USER]: {result}")
            return User.from_dict(result) if result else None
        except PyMongoError as e:
            ic(f"❌ Error en find_one: {e}")
            return None
    def find_ids_users(self) -> List[ObjectId]:
        """
        Devuelve solo los _id de todos los usuarios que NO sean Admin.
        """
        query = {"role": {"$ne": "Admin"}}
        projection = {"_id": 1}

        try:
            docs = self.db.find(self.users, query, projection) or []
            # Forzamos a lista si es un cursor
            if not isinstance(docs, list):
                docs = list(docs)
            return [doc["_id"] for doc in docs if "_id" in doc]
        except PyMongoError as e:
            ic(f"❌ Error en find_ids_users: {e}")
            raise

    def find_all(self, query: Optional[dict] = None, projection: Optional[dict] = None) -> List[User]:
        """
        Busca usuarios completos según query y proyección.
        Devuelve una lista de objetos User.
        """
        try:
            docs = self.db.find(self.users, query, projection) or []

            if not isinstance(docs, list):
                docs = list(docs)

            return [User.from_dict(doc) for doc in docs]
        except PyMongoError as e:
            ic(f"❌ Error en find_all: {e}")
            raise

    def count_documents(self, filtro: Optional[dict] = None) -> int:
        filtro = filtro or {}
        try:
            return self.db.count_documents(self.users, filtro)
        except PyMongoError as e:
            ic(f"Error en find_one: {e}")
            raise

    def find_blocked(self) -> int:
        try:
            query = {
               "blocked_until": { "$gt": datetime.now(timezone.utc) }
            }
            result = self.db.count_documents(self.users,query)
            return result if result else 0
        except PyMongoError as e:
            ic(f"Error en find_one: {e}")
            raise

    def create(self, user: User) -> bool:
        try:
            self.db.insert_with_log(self.users,user.to_dict())
            ic(f"Usuario creado: {user.username}")
            return True
        except PyMongoError as e:
            ic(f"Error en create: {e}")
            raise

    def update(self, query: dict, update: dict, upsert: bool = False, context: str = "") -> dict:
        return self.db.update_with_log(self.users, query, update, upsert, context=context)
        