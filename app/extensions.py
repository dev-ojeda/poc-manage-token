#!/usr/bin/env python
# -*- coding: utf-8 -*-
# app/extensions.py
from flask_bootstrap import Bootstrap
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.db_mongo import MongoDatabase
from app.logging_config import get_logger

# === Extensiones Flask ===
bootstrap = Bootstrap()
cors = CORS()
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# === Instancia global de Mongo (singleton) ===
db_mongo = MongoDatabase()

# === Logger del módulo ===
logger = get_logger("EXTENSIONS")

def init_extensions_log():
    """Emite logs una vez que el sistema de logging esté configurado."""
    try:
        logger.info("⚙️ Extensiones Flask inicializadas (Bootstrap, CORS, SocketIO, Limiter)")
        if db_mongo:
            logger.debug("Instancia global de MongoDB creada (sin conexión todavía)")
    except Exception as e:
        # Si el sistema de logging aún no está disponible
        print(f"[WARN] Error al emitir logs de extensiones: {e}")
