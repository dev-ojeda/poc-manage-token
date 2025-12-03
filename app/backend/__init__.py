from flask import Blueprint
from .routes_user import user_bp
from .routes_admin import admin_bp
from .routes_performance_api import performance_bp
from .route_metric import metrics_bp

backend_bp = Blueprint("backend", __name__, url_prefix="/api")

for bp in (user_bp, admin_bp, performance_bp, metrics_bp):
    backend_bp.register_blueprint(bp)