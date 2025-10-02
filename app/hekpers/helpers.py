from functools import wraps
from app.utils.db_mongo import MongoDatabase
import logging

def with_transaction(db: MongoDatabase):
    """
    Decorador para ejecutar un método de DAO dentro de una transacción.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            session = kwargs.pop("session", None)  # permite pasar session manualmente si se desea
            try:
                with db.client.start_session() as s:
                    # si ya hay session externa, usamos esa
                    session_to_use = session or s
                    with session_to_use.start_transaction():
                        result = func(*args, session=session_to_use, **kwargs)
                        return result
            except Exception as e:
                logging.error(f"❌ Transacción abortada en {func.__name__}: {e}")
                raise
        return wrapper
    return decorator
