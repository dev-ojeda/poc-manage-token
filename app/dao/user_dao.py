#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from pymongo.errors import PyMongoError
from pymongo.results import UpdateResult
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
    def find_one(self, query: dict = {}, projection: Optional[dict] = None) -> Optional[User]:
        try:
            result = self.db.find_one(collection=self.users, query=query, projection=projection)
            ic(f"[FIND ONE USER]: {result}")
            return User.from_dict(result) if result else None
        except PyMongoError as e:
            ic(f"❌ Error en find_one: {e}")
            raise
    def find_ids_users(self) -> List[User]:
        query = {"role": {"$ne": "Admin"}}
        projection = {"_id": 1}
        return self.find_all(query=query,projection=projection)

    def find_all(self, query: dict, projection: Optional[dict] = None) -> List[User]:
        try:
            return [User.from_dict(doc) for doc in self.db.find(self.users,query,projection)]
        except PyMongoError as e:
            ic(f"❌ Error en find_all: {e}")
            raise

    def count_documents(self, filtro: dict = {}) -> int:
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
            result = self.db.count_documents(self.collection[0],query)
            return result if result else None
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
        