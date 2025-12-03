#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import secrets
import time
import traceback
import uuid
from flask import Flask, Response, jsonify, request, g
from werkzeug.exceptions import HTTPException
from app.auth.exceptions.auth_exceptions import AuthException
from app.logging_config import get_logger


logger = get_logger("SECURITY")

def init_secure_headers(app: Flask) -> None:
    """Inicializa middleware de seguridad, cabeceras y manejo global de errores."""

    # ==========================
    # BEFORE REQUEST
    # ==========================
    @app.before_request
    def before_request() -> None:
        if request.method == "OPTIONS":
            return "", 204
        g.start_time = time.perf_counter()
        g.request_id = str(uuid.uuid4())
        g.csp_nonce = secrets.token_urlsafe(16)

    # ==========================
    # AFTER REQUEST
    # ==========================
    @app.after_request
    def set_headers(response: Response) -> Response:
        start_time = getattr(g, "start_time", None)
        duration = (time.perf_counter() - start_time) * 1000 if start_time else 0

        # --- Content Security Policy (CSP) ---
        if app.debug:
            # --- Content Security Policy ---
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "upgrade-insecure-requests; "
                "block-all-mixed-content;"
            )
        else:
            # Producción: solo con nonce y sin inline
            csp_policy = (
                "default-src 'self'; "
                f"script-src 'self' https://cdn.jsdelivr.net 'nonce-{g.csp_nonce}' 'unsafe-hashes'; "
                f"style-src 'self' https://cdn.jsdelivr.net 'nonce-{g.csp_nonce}'; "
                "img-src 'self' data:; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "upgrade-insecure-requests; "
                "block-all-mixed-content;"
            )

        # --- Security headers comunes ---
        response.headers.update({
            "X-App-Version": "1.0",
            "Content-Security-Policy": csp_policy,
            "X-Request-ID": g.get("request_id", "-"),
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Embedder-Policy": "require-corp",
        })

        # --- Control de caché adaptativo ---
        # Aplica "no-cache" solo a rutas autenticadas (ejemplo: /api, /auth, etc.)
        if request.path.startswith(("/api", "/auth", "/user")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        else:
            # Recursos estáticos: permitir caché por 7 días
            response.headers["Cache-Control"] = "public, max-age=604800"
        # Evita caching de respuestas con tokens o cabeceras de autenticación
        if "Authorization" in request.headers:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        # --- Logging de request ---
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = request.user_agent.string.splitlines()[0][:120]
        logger.info(
            f"[{g.get('request_id', '-')}] ⏱ {request.method} {request.path} "
            f"{response.status_code} - {duration:.2f} ms | {ip} | {ua}"
        )
        # --- Sanitización de posibles tokens JWT en la respuesta ---
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]
            if token in str(response.headers) or token in str(response.data):
                response.data = response.data.replace(token.encode(), b"[REDACTED]")
                for header, value in list(response.headers.items()):
                    if token in value:
                        response.headers[header] = value.replace(token, "[REDACTED]")

        # --- Declarar transporte de sesión basado en header ---
        response.headers["X-Session-Token-Transport"] = "header"
        response.headers["X-Token-Type"] = "Bearer"
        response.headers["Vary"] = "Authorization"
        return response

    # ==========================
    # CONTEXT PROCESSOR
    # ==========================
    current_year = datetime.datetime.now().year

    @app.context_processor
    def inject_year():
        return {"year": current_year, "csp_nonce": getattr(g, "csp_nonce", "")}

    # ==========================
    # HANDLERS DE ERRORES
    # ==========================
    @app.errorhandler(AuthException)
    def handle_auth_exception(e: AuthException) -> Response:
        error_id = g.get("request_id", str(uuid.uuid4()))
        logger.error(f"[{error_id}] JWT EXCEPTION: {str(e)}")
        response = jsonify({**e.to_dict(), "error_id": error_id})
        response.status_code = e.status
        response.headers["X-Error-ID"] = error_id
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException) -> Response:
        error_id = g.get("request_id", str(uuid.uuid4()))
        logger.error(f"[{error_id}] HTTP EXCEPTION: {e.name} ({e.code}) - {e.description}")
        response = jsonify({
            "message": e.description,
            "code": e.name,
            "status": e.code,
            "error_id": error_id
        })
        response.status_code = e.code
        response.headers["X-Error-ID"] = error_id
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(e: Exception) -> Response:
        error_id = g.get("request_id", str(uuid.uuid4()))
        logger.error(f"[{error_id}] Unhandled Exception: {traceback.format_exc()}")
        response = jsonify({
            "message": "Ha ocurrido un error inesperado.",
            "code": "InternalServerError",
            "status": 500,
            "error_id": error_id,
            **({"details": str(e), "traceback": traceback.format_exc()} if app.debug else {})
        })
        response.status_code = 500
        response.headers["X-Error-ID"] = error_id
        return response

    @app.errorhandler(429)
    def ratelimit_handler(e: Exception) -> Response:
        error_id = g.get("request_id", str(uuid.uuid4()))
        logger.warning(f"[{error_id}] RATE LIMIT: {str(e)}")
        response = jsonify({
            "msg": "Demasiadas solicitudes, espera un poco",
            "code": "RATE_LIMIT_EXCEEDED",
            "limit": str(getattr(e, "description", "")),
            "status": 429,
            "error_id": error_id
        })
        response.status_code = 429
        response.headers["X-Error-ID"] = error_id
        return response
