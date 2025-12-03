#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import time
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure, PyMongoError
from app.config import Config
from app.logging_config import get_logger


class MongoDatabase:
    """
    Conector MongoDB seguro y resiliente.
    - Singleton thread-safe
    - Reconexión automática
    - Verificación de conexión
    - Soporte de sesión
    """

    _instance_lock = threading.Lock()
    _initialized = False
    _client = None
    _db = None

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            with cls._instance_lock:
                if not hasattr(cls, "_instance"):
                    cls._instance = super(MongoDatabase, cls).__new__(cls)
        return cls._instance

    def __init__(self, uri: str = None, db_name: str = None, retry: int = 3, backoff: float = 0.5):
        if self._initialized:
            return

        self.logger = get_logger("MongoDatabase")
        self.uri = uri or Config.MONGO_URI_CLUSTER_X509
        self.db_name = db_name or Config.MONGO_DB
        self.tls_certificate_key_file = Config.MONGODB_X509
        self.retry = retry
        self.backoff = backoff

        if "." in self.db_name:
            raise ValueError(f"❌ Nombre de base de datos inválido: '{self.db_name}'")

        try:
            self.logger.info(f"🌐 Inicializando conexión MongoDB -> {self.uri}/{self.db_name}")
            self._client = MongoClient(
                self.uri,
                tlsCertificateKeyFile=self.tls_certificate_key_file,
                tls=True,
                server_api=ServerApi("1"),
                maxPoolSize=100,
                serverSelectionTimeoutMS=3000,
            )
            self._db = self._client[self.db_name]
            self._initialized = True
            self.logger.info("✅ Conexión inicializada correctamente.")
        except ConnectionFailure as e:
            self.logger.error(f"🚨 Falló la conexión inicial a MongoDB: {e}")
            self._initialized = False

    # ---------------------------------------------------
    #  CONTROL DE CONEXIÓN
    # ---------------------------------------------------
    def is_connected(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.admin.command("ping")
            return True
        except (ConnectionFailure, PyMongoError) as e:
            self.logger.warning(f"⚠️ Verificación fallida: {e}")
            return False

    def reconnect(self) -> bool:
        for attempt in range(1, self.retry + 1):
            try:
                self.logger.warning(f"🔄 Intentando reconexión MongoDB ({attempt}/{self.retry})...")
                self._client = MongoClient(
                    self.uri,
                    tlsCertificateKeyFile=self.tls_certificate_key_file,
                    tls=True,
                    server_api=ServerApi("1"),
                    maxPoolSize=100,
                    serverSelectionTimeoutMS=3000,
                )
                self._db = self._client[self.db_name]
                self._client.admin.command("ping")
                self.logger.info("✅ Reconexión exitosa.")
                return True
            except ConnectionFailure as e:
                self.logger.warning(f"⏳ Reconexión falló: {e}. Esperando {self.backoff}s...")
                time.sleep(self.backoff)
            except Exception as e:
                self.logger.exception(f"💥 Error inesperado al reconectar: {e}")
                time.sleep(self.backoff)
        self.logger.error("🚫 No se pudo reconectar a MongoDB después de varios intentos.")
        return False

    # ---------------------------------------------------
    #  SESIONES MONGO
    # ---------------------------------------------------
    def start_session(self):
        if not self.is_connected():
            self.logger.warning("⚠️ MongoDB desconectado. Intentando reconexión...")
            if not self.reconnect():
                raise ConnectionFailure("No se pudo iniciar sesión: MongoDB desconectado.")
        return self._client.start_session()

    # ---------------------------------------------------
    #  ACCESO PÚBLICO
    # ---------------------------------------------------
    @property
    def client(self) -> MongoClient:
        if self._client is None:
            self.logger.debug("Creando cliente MongoDB on-demand.")
            self._client = MongoClient(
                self.uri,
                tls=True,
                tlsCertificateKeyFile=self.tls_certificate_key_file,
                server_api=ServerApi("1"),
                maxPoolSize=100,
                serverSelectionTimeoutMS=3000,
            )
            self._db = self._client[self.db_name]
        return self._client

    @property
    def db(self):
        if self._db is None:
            self._db = self.client[self.db_name]
        return self._db

    # ---------------------------------------------------
    #  CIERRE CONTROLADO
    # ---------------------------------------------------
    def close(self, force: bool = False):
        """
        Cierra la conexión MongoDB de forma segura.
        Si 'force' es True, reinicia completamente la instancia.
        """
        if self._client:
            try:
                self._client.close()
                self.logger.info("🛑 Conexión MongoDB cerrada correctamente.")
            except Exception as e:
                self.logger.warning(f"⚠️ Error al cerrar cliente MongoDB: {e}")

        if force:
            self.logger.info("♻️ Reiniciando instancia MongoDatabase por cierre forzado.")
            self._client = None
            self._db = None
            self._initialized = False
