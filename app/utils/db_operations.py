import functools
from pymongo.errors import AutoReconnect, PyMongoError, ConnectionFailure, OperationFailure
from app.log_config import setup_logging
from app.utils.db_mongo import MongoDatabase

logger = setup_logging().getChild(f"MONGO_OP_AND_RETRY.{__name__}")

# def mongo_op(_func=None, *, use_session=True, contextual=True, backoff=0.5, max_attempts=3, context_name=None):
#     """
#     Decorador robusto para operaciones MongoDB.
#     - Reintenta errores transitorios.
#     - Controla sesiones automáticamente.
#     - Implementa backoff exponencial.
#     - Logging contextual seguro para entornos concurrentes.
#     """

#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             attempts = 0
#             session: ClientSession | None = None

#             # Detección dinámica de self
#             self_ref = args[0] if args and hasattr(args[0], "__dict__") else None
#             db_ref = getattr(self_ref, "db", None) if self_ref else None
#             context = context_name or func.__name__

#             while True:
#                 try:
#                     # Crear sesión si aplica
#                     if use_session and db_ref is not None and getattr(db_ref, "client", None) is not None:
#                         session = db_ref.client.start_session()
#                         kwargs["session"] = session

#                     # Ejecutar operación
#                     result = func(*args, **kwargs)
#                     return result

#                 except (PyMongoError, ConnectionFailure, OperationFailure) as e:
#                     attempts += 1
#                     wait_time = backoff * (2 ** (attempts - 1))
#                     msg = f"[{context}] Intento {attempts}/{max_attempts} fallido: {e.__class__.__name__} - {e}"

#                     if attempts < max_attempts:
#                         logger.warning(f"{msg}. Reintentando en {wait_time:.2f}s...")
#                         time.sleep(wait_time)
#                     else:
#                         logger.error(f"{msg}. Límite alcanzado. Abortando.")
#                         raise

#                 finally:
#                     if session is not None:
#                         try:
#                             session.end_session()
#                         except Exception as e:
#                             logger.warning(f"[{context}] Error al cerrar sesión: {e}")
#                         finally:
#                             session = None

#         return wrapper

#     return decorator if _func is None else decorator(_func)

def mongo_op(fn):
    """
    Decorador para envolver operaciones MongoDB con:
    - Manejo de sesión (si existe)
    - Manejo automático de reconexión
    - Logging uniforme
    - Control de errores PyMongo
    """

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        db: MongoDatabase = getattr(self, "db", None)
        context = kwargs.get("context", fn.__name__)

        if db is None:
            logger.error(f"🚨 [{context}] Database reference is None (DAO: {self.__class__.__name__})")
            return {"success": False, "error": "Database not initialized", "context": context}

        try:
            # Si ya viene una sesión activa (por ejemplo desde un middleware o transacción)
            session = kwargs.get("session")
            if session:
                logger.debug(f"🔁 [{context}] Using provided MongoDB session")
                return fn(self, *args, **kwargs)

            # Si no hay sesión, crear una temporal
            with db.client.start_session() as session:
                kwargs["session"] = session
                logger.debug(f"⚙️ [{context}] Started MongoDB session for {fn.__name__}")
                result = fn(self, *args, **kwargs)
                return result

        except (AutoReconnect, ConnectionFailure) as e:
            logger.warning(f"🔄 [{context}] MongoDB reconnect triggered: {e}")
            try:
                db.reconnect()
                with db.client.start_session() as session:
                    kwargs["session"] = session
                    result = fn(self, *args, **kwargs)
                    return result
            except Exception as retry_error:
                logger.exception(f"💥 [{context}] Retry failed: {retry_error}")
                return {"success": False, "error": str(retry_error), "context": context}

        except OperationFailure as e:
            logger.error(f"🚫 [{context}] Operation failed: {e}")
            return {"success": False, "error": str(e), "context": context}

        except PyMongoError as e:
            logger.error(f"❗ [{context}] PyMongo error: {e}")
            return {"success": False, "error": str(e), "context": context}

        except Exception as e:
            logger.exception(f"💥 [{context}] Unexpected error: {e}\n{traceback.format_exc()}")
            return {"success": False, "error": str(e), "context": context}

    return wrapper