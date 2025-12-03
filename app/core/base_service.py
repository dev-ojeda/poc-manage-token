# app/core/base_service.py
from typing import Optional, TypeVar, Generic
from pymongo.errors import ConnectionFailure, PyMongoError
from app.extensions import db_mongo
from app.logging_config import get_logger

T = TypeVar("T")  # tipo genérico de DAO

class BaseService(Generic[T]):
    """Clase base para todos los servicios: logger, conexión DB, DAO y resiliencia Mongo."""

    dao: Optional[T] = None

    def __init__(self, db=None, dao: Optional[T] = None, logger=None):
        self.db = db or db_mongo
        self.logger = logger or get_logger(self.__class__.__name__)
        self.dao = dao or getattr(self, "dao", None)
        self._validate_dependencies()

    def _validate_dependencies(self):
        if not self.db:
            raise RuntimeError(f"{self.__class__.__name__}: instancia de DB no válida.")
        if not self.dao:
            self.logger.warning(f"{self.__class__.__name__}: sin DAO asociado explícitamente.")

    # -------------------------
    # LOGGING UNIFICADO
    # -------------------------
    def _log_debug(self, msg: str, **kwargs):
        self.logger.debug(f"{self.__class__.__name__} → {msg}", extra=kwargs)

    def _log_info(self, msg: str, **kwargs):
        self.logger.info(f"{self.__class__.__name__} → {msg}", extra=kwargs)

    def _log_error(self, msg: str, exc: Exception = None, **kwargs):
        self.logger.error(f"{self.__class__.__name__} → {msg}: {exc}", extra=kwargs)

    # -------------------------
    # EJECUCIÓN SEGURA
    # -------------------------
    def _safe_exec(self, func, *args, context: str = "", **kwargs):
        """
        Ejecuta DAO o query con manejo automático de errores y reconexión Mongo.
        """
        try:
            self._log_debug(f"Ejecutando DAO: {context or func.__name__}")

            # Verifica conexión antes
            if not self.db.is_connected():
                self.logger.warning(f"⚠️ Mongo desconectado. Intentando reconexión ({self.__class__.__name__})...")
                if not self.db.reconnect():
                    raise ConnectionFailure("No se pudo reconectar con MongoDB.")

            return func(*args, **kwargs)

        except (ConnectionFailure, PyMongoError) as e:
            self._log_error("Fallo en conexión Mongo", exc=e)
            # Reintento automático una sola vez
            if self.db.reconnect():
                self._log_info("🔁 Reintentando operación tras reconexión exitosa.")
                return func(*args, **kwargs)
            raise
        except Exception as e:
            self._log_error(f"Error en {context or func.__name__}", exc=e)
            raise
