#!/usr/bin/env python
# -*- coding: utf-8 -*-
# middlewares/security.py

from flask import request
from icecream import ic


def apply_secure_headers(app):
    @app.after_request
    def set_headers(response):
        response.headers['X-App-Version'] = '1.0'

        # Seguridad
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # CORS
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        ic(f"[REQUEST_PATH] - {request.path}")
        # Control de caché según tipo de recurso
        if request.path.startswith("/static"):
            response.headers['Cache-Control'] = 'public, max-age=3600, immutable'
            # Forzar Connection: close si es API o error crítico
        elif (request.path.startswith("/api") or response.status_code in (401, 403)): # Opcionalmente puedes agregar más
            # Cierre explícito de conexión HTTP
            response.headers["Connection"] = "close"
        else:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        

        return response
