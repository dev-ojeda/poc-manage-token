#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask

from app.midleware.headers import init_headers   
from app.midleware.errors import init_middlewares
from app.midleware.security import init_secure_headers
from app.extensions import cors, bootstrap, socketio, limiter
from app.config import Config


def create_app(config_class=Config):
    """Crea e inicializa la aplicación Flask."""
    app = Flask(__name__.split(".", maxsplit=1)[0])
    app.config.from_object(config_class)
    # Middlewares
    init_headers(app=app)
    init_middlewares(app=app)
    init_secure_headers(app=app)
    # Inicializar extensiones
    limiter.init_app(app=app)
    socketio.init_app(app=app,async_mode="eventlet", cors_allowed_origins=Config.CORS_ORIGINS, cors_credentials=True, ping_timeout=25, ping_interval=10)
    bootstrap.init_app(app=app)
    cors.init_app(app=app, resources={r"/*": {"origins": Config.CORS_ORIGINS}}, supports_credentials=True)
    # Registrar blueprints
    with app.app_context():
        register_blueprints(app)
    return app
    

def register_blueprints(app):
    from app.backend.routes_admin import admin_bp
    from app.backend.routes import backend_bp
    from app.frontend.routes import frontend_bp
    from app.utils.db_manager import db_Manager_bp
    from app.web_socket.event_socket import socketio_bp
    from app.backend.routes_performance_api import performance_bp
    from app.backend.route_metric import metrics_bp
    app.register_blueprint(backend_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(performance_bp, url_prefix="/api")
    app.register_blueprint(metrics_bp)
    app.register_blueprint(frontend_bp)
    app.register_blueprint(db_Manager_bp)
    app.register_blueprint(socketio_bp)
