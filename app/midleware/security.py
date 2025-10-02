#!/usr/bin/env python
# -*- coding: utf-8 -*-
# middlewares/security.py
import time
import logging
import traceback
import uuid
from flask import jsonify, request
from flask.globals import g
from app.auth.exceptions.auth_exceptions import AuthException

IGNORED_PATHS = [
    "/",
    "/health",
    "/static",
    "/favicon.ico",
    "/api/auth/admin/dashboard",
    "/api/metrics/timeline",   # ✅ corregido singular
    "/dashboard",
    "/.well-known/appspecific/com.chrome.devtools.json",
]

IGNORED_ENDPOINTS = [
    "/",
    "/api/metrics/timeline",   # ✅ corregido singular
    "/api/metrics/alerts",
    "/api/metrics/performance",
    "/api/auth/admin/dashboard",
    "/dashboard",
    "/.well-known/appspecific/com.chrome.devtools.json",
]


def is_ignored(path: str) -> bool:
    """Revisa si el path debe excluirse de métricas y logging."""
    return any(path == p or path.startswith(p + "/") for p in IGNORED_PATHS)


def is_ignored_endpoints(path: str) -> bool:
    """Revisa si el endpoints debe excluirse de métricas y logging."""
    return any(path == p or path.startswith(p + "/") for p in IGNORED_ENDPOINTS)


def init_secure_headers(app):
   # =========================
    # Before Request
    # =========================
    @app.before_request
    def before_request():
        if request.method == "OPTIONS":
            return "", 204
        g.start_time = time.perf_counter()
        g.request_id = str(uuid.uuid4())   # ✅ correlación única por request

    # =========================
    # After Request
    # =========================
    @app.after_request
    def set_headers(response):
        duration = (time.perf_counter() - g.start_time) * 1000 if hasattr(g, "start_time") else 0
        response.headers["X-App-Version"] = "1.0"
        response.headers["X-Request-ID"] = g.get("request_id", "-")   # ✅ siempre presente

        # Seguridad
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "no-referrer"
        ...
        # Logging con request_id
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = request.user_agent.string[:120]
        log_msg = f"[{g.request_id}] ⏱ {request.method} {request.path} {response.status_code} - {duration:.2f} ms | {ip} | {ua}"
        logging.info(log_msg)
        ...
        return response

    # =========================
    # Error Handlers
    # =========================
    @app.errorhandler(AuthException)
    def handle_auth_exception(e: AuthException):
        error_id = g.get("request_id", str(uuid.uuid4()))
        response = jsonify({**e.to_dict(), "error_id": error_id})
        response.status_code = e.status
        response.headers["X-Error-ID"] = error_id
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(e: Exception):
        error_id = g.get("request_id", str(uuid.uuid4()))
        logging.error(f"[{error_id}] Unhandled Exception: {traceback.format_exc()}")
        response = jsonify({
            "message": "Ha ocurrido un error inesperado. 🚨",
            "code": "InternalServerError",
            "status": 500,
            "error_id": error_id,
            "details": str(e) if app.debug else None,
            "traceback": traceback.format_exc() if app.debug else None,
        })
        response.status_code = 500
        response.headers["X-Error-ID"] = error_id
        return response
