#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import timezone
import json
import traceback
import logging
from typing import Optional
from pymongo.mongo_client import MongoClient, PyMongoError
from pymongo.server_api import ServerApi
from pymongo.results import InsertOneResult, UpdateResult
from app.config import Config
from icecream import ic
from app.extensions import socketio  # Importar la instancia global de SocketIO

class MongoDatabase:
    def __init__(self) -> None:
        """Inicializa la conexión a MongoDB"""
        self.db_name = Config.MONGO_DB
        self.uri = Config.MONGO_URI_CLUSTER_X509
        self.client: Optional[MongoClient] = None
        self.tls = True
        self.tlsCertificateKeyFile = Config.MONGODB_X509
        self.server_api=ServerApi('1')
        self.db = None
        self.connect()
         # Configurar logger correctamente
        self.logger = logging.getLogger("MongoMonitor")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:  # Evita múltiples handlers si ya existen
            self.logger.addHandler(handler)

    def connect(self) -> None:
        """Conecta a MongoDB"""
        try:
            self.client = MongoClient(self.uri, tls=self.tls, tlsCertificateKeyFile=self.tlsCertificateKeyFile, server_api=self.server_api,tz_aware=True, tzinfo=timezone.utc)
            self.db = self.client[self.db_name]
            ic(f"Conectado a MongoDB -> {self.db_name}")
        except PyMongoError as e:
            ic(f"Error al conectar a MongoDB: {e}")
            raise

    def close(self) -> None:
        """Cierra la conexión a MongoDB"""
        if self.client:
            self.client.close()
            ic("Conexión a MongoDB cerrada")

    def insert_one(self, collection: str, document: dict) -> InsertOneResult:
        """Inserta un solo documento"""
        try:
            return self.db[collection].insert_one(document)
        except PyMongoError as e:
            ic(f"Error al insertar: {e}")
            raise

    def insert_many(self, collection: str, documents: list[dict]) -> list:
        """Inserta múltiples documentos"""
        try:
            result = self.db[collection].insert_many(documents)
            ic("Documentos insertados en batch correctamente")
            return result.inserted_ids
        except PyMongoError as e:
            ic(f"Error en batch insert: {e}")
            raise

    def find(self, collection: str, query: Optional[dict] = None, projection: Optional[dict] = None) -> list[dict]:
        """Realiza una búsqueda y retorna una lista de documentos"""
        query = query or {}
        projection = projection or {}
        try:
            result = list(self.db[collection].find(query, projection))
            return result if result else None
        except PyMongoError as e:
            ic(f"Error en búsqueda: {e}")
            return None

    def find_one(self, collection: str, query: Optional[dict] = None, projection: Optional[dict] = None) -> Optional[dict]:
        """Devuelve un solo documento"""
        query = query or {}
        projection = projection or {}
        try:
            result = self.db[collection].find_one(query,projection)
            return result if result else None 
        except PyMongoError as e:
            ic(f"Error en find_one: {e}")
            return None

    def count_documents(self, collection: str, filtro: Optional[dict] = None) -> int:
        """Cuenta documentos que cumplan cierto filtro (vacío = total)"""
        filtro = filtro or {}
        try:
            return self.db[collection].count_documents(filtro)
        except PyMongoError as e:
            ic(f"Error en find_one: {e}")
            raise

    def update_many(self, collection: str, query: dict, update: dict):
        """Actualiza múltiples documentos que coincidan con la consulta"""
        try:
            result = self.db[collection].update_many(filter=query,update=update,upsert=True)
            ic(f"Documentos coincidentes: {result.matched_count}")
            ic(f"Documentos modificados: {result.modified_count}")
            if result.modified_count > 0:
                ic(f"{result.modified_count} documentos actualizados exitosamente.")
            elif result.matched_count > 0:
                ic("Los documentos ya tenían los valores especificados.")
            else:
                ic("No se encontraron documentos que coincidan con la consulta.")
            return result.modified_count
        except PyMongoError as e:
            ic(f"Error al actualizar múltiples documentos: {e}")
            raise

    def update_one_revoked(self, collection: str, query: dict, update: dict, upsert: bool) -> UpdateResult:
        """Actualiza un solo documento"""
        return self.db[collection].update_one(query, update, upsert)

    def update_mark_token_as_used(self, collection: str, query: dict, update: dict, upsert: bool):
        """Actualiza un solo documento"""
        try:
            result = self.db[collection].update_one(query, update, upsert)
            if result.modified_count == 1:
                ic(f"Documento actualizado exitosamente. {result.modified_count}")
            elif result.matched_count == 1 and result.modified_count == 0:
                ic("El documento ya tenía los valores especificados.")
            else:
                ic("No se encontró el documento para actualizar o hubo un error.")
            return bool(result.modified_count) 
        except PyMongoError as e:
            ic(f"Error al actualizar: {e}")
            raise

    def update_one(self, collection: str, query: dict, update: dict, upsert: bool):
        """Actualiza un solo documento"""
        try:
            result = self.db[collection].update_one(query, update, upsert)
            if result.modified_count == 1:
                ic(f"Documento actualizado exitosamente. {result.modified_count}")
            elif result.matched_count == 1 and result.modified_count == 0:
                ic("El documento ya tenía los valores especificados.")
            else:
                ic("No se encontró el documento para actualizar o hubo un error.")
            return result.modified_count 
        except PyMongoError as e:
            ic(f"Error al actualizar: {e}")
            raise

    def delete_one(self, collection: str, query: dict) -> bool:
        """Elimina un documento"""
        try:
            result = self.db[collection].delete_one(query)
            ic(f"Documentos eliminados: {result.deleted_count}")
            return result.deleted_count > 0
        except PyMongoError as e:
            ic(f"Error al eliminar: {e}")
            raise

    def watch_sessions_for_admin(self):
        with self.db["refresh_tokens"].watch() as stream:
            ic("⏱️ Escuchando cambios en sesiones...")
            for change in stream:
                ic("🔄 Cambio detectado:", json.dumps(change, indent=2))
                # Aquí puedes filtrar por rol si el documento completo está en `fullDocument`
                full_doc = change.get("fullDocument")
                if full_doc and full_doc.get("username") not in ["admin@example.com"]:
                    continue  # Ignorar cambios de roles no admin
                # Enviar evento, notificación o actualizar cache, etc.
                socketio.emit('admin_session_update', {"msg": "Sesión de admin actualizada"}, broadcast=True)

    def insert_with_log(self, collection: str, document: dict, context: str = "") -> dict:
        """
        Realiza un insert_one seguro con manejo de errores y log contextual.

        :param collection: Colección PyMongo (db.coleccion)
        :param document: Documento a insertar (dict)
        :param context: Nombre del módulo o acción (ej: "Login", "AuditLog")
        :return: Dict con resultado y mensaje
        """
        prefix = f"[{context}] " if context else ""

        try:
            with self.client.start_session() as session:
                with session.start_transaction():
                    result: InsertOneResult = self.db[collection].insert_one(document, session=session)
                    if result.acknowledged and result.inserted_id:
                        msg = f"{prefix}✅ Documento insertado correctamente: {result.inserted_id}"
                    else:
                        msg = f"{prefix}⚠️ Inserción sin confirmación o sin ID."
                    self.logger.info(msg)
                    return {
                        "success": True,
                        "context": context,
                        "acknowledged": result.acknowledged,
                        "inserted_id": result.inserted_id,
                        "message": msg
                    }
 
        except PyMongoError as e:
            msg = f"{prefix}❌ Error al insertar en MongoDB: {e.__class__.__name__}: {e}"
            self.logger.error(msg)
            ic(msg)
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "context": context,
                "trace": traceback.format_exc(),
                "message": msg
            }

    def update_with_log(self, collection: str, query: dict, update: dict, upsert: bool, context: str = "") -> dict:
        """
        Realiza un update_one seguro con manejo de errores y log contextual.

        :param collection: Nombre de la colección
        :param query: Filtro para seleccionar el documento a actualizar
        :param update: Operación de actualización (ej. {"$set": {...}})
        :param context: Contexto para el log (ej. "Logout", "AuditUpdate")
        :return: Diccionario con el resultado de la operación
        """
        prefix = f"[{context}] " if context else ""

        try:
            with self.client.start_session() as session:
                with session.start_transaction():
                    result: UpdateResult = self.db[collection].update_one(query, update, upsert, session=session)
                    if result.matched_count == 0:
                        msg = f"{prefix}⚠️ No se encontró ningún documento para actualizar."
                    elif result.modified_count == 0:
                        msg = f"{prefix}ℹ️ Documento encontrado, pero no hubo cambios (ya estaba actualizado)."
                    else:
                        msg = f"{prefix}✅ Documento actualizado correctamente."

                    self.logger.info(msg)
                    return {
                        "success": True,
                        "context": context,
                        "matched_count": result.matched_count,
                        "modified_count": result.modified_count,
                        "acknowledged": result.acknowledged,
                        "message": msg
                    }

        except PyMongoError as e:
            msg = f"{prefix}❌ Error al actualizar en MongoDB: {e.__class__.__name__}: {e}"
            self.logger.error(msg)
            traceback.print_exc()
            return {
                "success": False,
                "context": context,
                "error": str(e),
                "trace": traceback.format_exc(),
                "message": msg
            }

    def aggregate(self, collection: str, pipeline: list):
        try:
            with self.client.start_session() as session:
                with session.start_transaction():
                    result = list(self.db[collection].aggregate(pipeline=pipeline,session=session))
                    return result
        except PyMongoError as e:
            msg = f"❌ Error al List en MongoDB: {e.__class__.__name__}: {e}"
            self.logger.error(msg)
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "trace": traceback.format_exc(),
                "message": msg
            }
        





