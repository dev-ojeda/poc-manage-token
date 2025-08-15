#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask
from app.extensions import bootstrap, cors, socketio
from app.midleware.security import apply_secure_headers 
from app.config import Config


def create_app():
    """Crea e inicializa la aplicación Flask."""
    app = Flask(__name__.split(".")[0])
    # Registrar blueprints
    with app.app_context():
        register_blueprints(app)

    apply_secure_headers(app)  # ⬅️ inyectamos aquí
    # Inicializar extensiones
     # Inicializar extensiones
    socketio.init_app(app,async_mode="eventlet", cors_allowed_origins=Config.CORS_ORIGINS, cors_credentials=True, ping_timeout=25, ping_interval=10)
    bootstrap.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": Config.CORS_ORIGINS}}, supports_credentials=True)
    return app
    

def register_blueprints(app):
    from app.backend.routes_admin import admin_bp
    from app.backend.routes import backend_bp
    from app.frontend.routes import frontend_bp
    from app.utils.db_manager import db_Manager_bp
    from app.web_socket.event_socket import socketio_bp
    app.register_blueprint(backend_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(frontend_bp)
    app.register_blueprint(db_Manager_bp)
    app.register_blueprint(socketio_bp)
