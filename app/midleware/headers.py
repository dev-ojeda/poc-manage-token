import time
from flask import request, g
from app.config import Config

def init_headers(app):
    @app.before_request
    def before_request():
        if request.method == "OPTIONS":
            return "", 204
        g.start_time = time.perf_counter()

    @app.after_request
    def set_headers(response):
        # Versionado
        response.headers["X-App-Version"] = "1.0"

        # Seguridad
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["Referrer-Policy"] = "no-referrer"

        # CORS
        origin = request.headers.get("Origin")
        if origin and origin in Config.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Token-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"

        # Cache control
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

