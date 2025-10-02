import datetime
import uuid
import logging
import traceback
from flask import jsonify
from app.auth.exceptions.auth_exceptions import AuthException

def init_middlewares(app):
    @app.errorhandler(AuthException)
    def handle_auth_exception(e: AuthException):
        response = jsonify(e.to_dict())
        response.status_code = e.status
        return response

    @app.context_processor
    def inject_year():
        return {"year": datetime.datetime.now().year}

    @app.errorhandler(Exception)
    def handle_generic_exception(e: Exception):
        error_id = str(uuid.uuid4())
        logging.error(f"Unhandled Exception [{error_id}]: {traceback.format_exc()}")
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
    @app.errorhandler(429)
    def ratelimit_handler(e: Exception):
        response = jsonify({
            "msg": "⏳ Demasiadas solicitudes, espera un poco",
            "code": "RATE_LIMIT_EXCEEDED",
            "limit": str(e.description),
            "status": 429
        })
        return response
