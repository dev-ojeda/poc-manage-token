#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import signal
import sys
import eventlet
import eventlet.wsgi
from app import create_app
from app.config import Config
from app.extensions import db_mongo
from app.logging_config import get_logger
# ======================
# APP Initialization
# ======================
app = create_app(config_class=Config)
logger = get_logger("WSGI_MAIN")
def main() -> None:
    """
    Punto de entrada principal de la aplicación Flask con Eventlet.
    Soporta SSL y cierre ordenado del servidor + MongoDB.
    """
    use_ssl = os.getenv("FLASK_USE_SSL", "false").lower() == "true"
    listener = eventlet.listen((Config.HOST, Config.PORT))

    if use_ssl:
        ssl_args = {
            "certfile": Config.PATH_CRT,
            "keyfile": Config.PATH_KEY,
            "server_side": True
        }
        listener = eventlet.wrap_ssl(listener, **ssl_args)
        logger.info(f"🔒 HTTPS escuchando en https://{Config.HOST}:{Config.PORT}")
    else:
        logger.info(f"🚀 HTTP escuchando en http://{Config.HOST}:{Config.PORT}")

    # ======================
    # Cierre ordenado
    # ======================
    def graceful_shutdown(*_):
        logger.info("🧹 Cerrando servidor y conexión MongoDB...")
        try:
            if db_mongo and getattr(db_mongo, "client", None):
                db_mongo.close()
                logger.info("✅ Conexión MongoDB cerrada correctamente.")
        except Exception as e:
            logger.warning(f"⚠️ Error al cerrar MongoDB: {e}")
        finally:
            logger.info("🛑 Servidor detenido correctamente.")
            sys.exit(0)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # ======================
    # Lanzar servidor WSGI
    # ======================
    try:
        eventlet.wsgi.server(listener, app, log_output=False)
    except Exception as e:
        logger.error(f"❌ Error crítico en el servidor WSGI: {e}")
        graceful_shutdown()

if __name__ == "__main__":
    main()
