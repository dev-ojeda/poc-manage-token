import time
from functools import wraps

import time
import logging
from functools import wraps
from pymongo.client_session import ClientSession
from pymongo.errors import PyMongoError

def mongo_op(_func=None, *, use_session=True, contextual=True, backoff=0.5, max_attempts=3):
    """
    Decorador para operaciones MongoDB:
    - Reintenta automáticamente en caso de excepción.
    - Si use_session=True, inicia una sesión y commit/abort de forma automática.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            attempts = 0
            while True:
                session: ClientSession = None
                try:
                    # Iniciar sesión si corresponde
                    if use_session and hasattr(self.db, 'client'):
                        session = self.db.client.start_session()
                        kwargs['session'] = session

                    result = func(self, *args, **kwargs)

                    # Commit automático si hay sesión
                    if session:
                        session.end_session()
                    return result
                except PyMongoError as e:
                    attempts += 1
                    if session:
                        session.end_session()
                    if attempts >= max_attempts:
                        logging.error(f"[{func.__name__}] Excedido máximo reintentos ({max_attempts}): {e}")
                        raise
                    logging.warning(f"[{func.__name__}] Error: {e}. Reintentando {attempts}/{max_attempts} en {backoff}s...")
                    time.sleep(backoff)
        return wrapper

    if _func is None:
        return decorator
    else:
        return decorator(_func)

