# app/__init__.py
import logging
import importlib
import os
import pkgutil
from flask import Blueprint, Flask
from app.extensions import cors, bootstrap, socketio, limiter, db_mongo, init_extensions_log
from app.midleware.security import init_secure_headers
from app.config import Config
from app.logging_config import get_logger


def create_app(config_class=Config) -> Flask:
    """Crea la aplicación Flask y registra automáticamente blueprints."""
    logger = get_logger("CREATE_APP")
    logging.getLogger("werkzeug").disabled = True

    app = Flask(__name__)
    app.config.from_object(config_class)

    logger.info(f"🔐 SECRET_KEY configurada: {bool(app.config.get('SECRET_KEY'))}")
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.urandom(32)

    init_extensions_log()

    if db_mongo.db is not None and db_mongo.is_connected():
        logger.info("✅ MongoDB conectado correctamente")
    else:
        logger.warning("⚠️ MongoDB no respondió al ping inicial")

    init_secure_headers(app)
    limiter.init_app(app)
    socketio.init_app(
        app,
        async_mode="eventlet",
        cors_allowed_origins=Config.CORS_ORIGINS,
        cors_credentials=True,
        ping_timeout=25,
        ping_interval=10,
    )
    bootstrap.init_app(app)
    cors.init_app(
        app,
        resources={r"/*": {"origins": Config.CORS_ORIGINS}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Content-Disposition"],
    )

    register_all_blueprints(app, logger)
    logger.info("🚀 App Flask creada con éxito")

    return app


def register_all_blueprints(app: Flask, logger: logging.Logger):
    """Escanea dinámicamente los paquetes y registra todos los Blueprints encontrados."""
    packages = ["app.backend", "app.frontend"]
    total_registered = 0

    for package_name in packages:
        try:
            package = importlib.import_module(package_name)
        except ModuleNotFoundError:
            logger.warning(f"❌ Paquete no encontrado: {package_name}")
            continue

        for _, mod_name, is_pkg in pkgutil.iter_modules(package.__path__):
            if is_pkg:
                continue

            full_mod_name = f"{package_name}.{mod_name}"
            try:
                mod = importlib.import_module(full_mod_name)
            except Exception as e:
                logger.warning(f"⚠️ No se pudo importar {full_mod_name}: {e}")
                continue

            found = False
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, Blueprint):
                    app.register_blueprint(attr)
                    logger.info(f"🧩 Blueprint registrado: {attr.name} ({full_mod_name})")
                    total_registered += 1
                    found = True

            if not found:
                logger.debug(f"ℹ️ Módulo sin Blueprint: {full_mod_name}")

    logger.info(f"✅ Total de Blueprints registrados: {total_registered}")
