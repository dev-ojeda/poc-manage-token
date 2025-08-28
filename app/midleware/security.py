#!/usr/bin/env python
# -*- coding: utf-8 -*-
# middlewares/security.py

import logging
import traceback
from flask import jsonify, request
from icecream import ic

from app.auth import AuthException


def apply_secure_headers(app):
    @app.after_request
    def set_headers(response):
        response.headers['X-App-Version'] = '1.0'

        # Seguridad
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "no-referrer"
        # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; object-src 'none'"

        # CORS (ajustar en prod)
        response.headers["Access-Control-Allow-Origin"] = "https://localhost:5000/"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Token-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"

        # Control de caché
        if request.path.startswith("/static"):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif (request.path.startswith("/auth") or response.status_code in (401, 403)):
            response.headers["Connection"] = "close"
        else:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

     # --- manejador de AuthException ---
    @app.errorhandler(AuthException)
    def handle_auth_exception(e: AuthException):
        response = jsonify(e.to_dict())
        response.status_code = e.status
        return response
    # --- manejador global ---
    @app.errorhandler(Exception)
    def handle_generic_exception(e: Exception):
        logging.error("Unhandled Exception: %s", traceback.format_exc())
        response = jsonify({
            "message": "Ha ocurrido un error inesperado. 🚨",
            "code": "InternalServerError",
            "status": 500,
            "details": str(e) if app.debug else None
        })
        response.status_code = 500
        return response