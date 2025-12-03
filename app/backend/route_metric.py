#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from flask import Blueprint, json, jsonify, request
from icecream import ic
from app import limiter
from app.auth.services.metrics_service import MetricService
from app.midleware.jwt_guard import jwt_admin_required
from app.model.metrics_model import MetricModel

ic.configureOutput(prefix="METRICS:", includeContext=__name__, lineWrapWidth=500)
ic.contextDelimiter = " "

metrics_bp = Blueprint("metrics", __name__, url_prefix="/metrics")
EXCLUDED_PATHS = ["/", "https://localhost:5000/api/metrics/collect-api", "https://localhost:5000/api/metrics/collect-web-vitals","https://localhost:5000/api/metrics/timeline"]
EXCLUDED_PREFIXES = ["/static"]
# -----------------------------
# Helpers
# -----------------------------
def safe_jsonify(data, status: int = 200):
    """Envuelve jsonify con manejo de errores de conexión."""
    try:
        resp = jsonify(data)
        resp.status_code = status
        return resp
    except GeneratorExit:
        ic("Cliente cerró la conexión antes de recibir la respuesta")
        return "", 499
    except Exception as e:
        ic(f"Error al generar respuesta JSON: {e}")
        return jsonify({"error": "Internal server error"}), 500

def _is_excluded_page(page: str) -> bool:
    """Revisa si la página debe ser ignorada."""
    return page in EXCLUDED_PATHS or any(page.startswith(p) for p in EXCLUDED_PREFIXES)

class MetricsEndpoints:
    service = MetricService()

    @staticmethod
    @jwt_admin_required
    def collect_webvitals(user):
        if not request.is_json:
            return jsonify({"msg": "Content-Type debe ser application/json", "code": "INVALID_JSON"}), 400
    
        data = request.get_json()
        data_metric = data.get("metrics", [])
        if not isinstance(data_metric, list):
            return jsonify({"msg": "metrics debe ser una lista", "code": "INVALID_FORMAT"}), 400

        # Verificar si todas las métricas tienen `url`
        for metric in data_metric:
            page = metric.get("url")
            if page and _is_excluded_page(page):
                return safe_jsonify({"status": "ignored"})
        ic(data_metric)
        metric_model = MetricModel.from_documents(data_metric)
        # Convertirlos en dicts listos para MongoDB (timestamp como datetime real)
        docs = [m.to_dict() for m in metric_model]
        ic(docs)
        MetricsEndpoints.service.create_metrics(metric=docs)
        return safe_jsonify({"status": "stored"})
    @staticmethod
    @jwt_admin_required
    @limiter.limit("10/minute")  # rate limit específico
    def collect_api(user):
        if not request.is_json:
            return jsonify({"msg": "Content-Type debe ser application/json", "code": "INVALID_JSON"}), 400
        data = request.get_json()
        data_metric = data.get("metrics", [])
        if not isinstance(data_metric, list):
            return jsonify({"msg": "metrics debe ser una lista", "code": "INVALID_FORMAT"}), 400

        # Verificar si todas las métricas tienen `url`
        for metric in data_metric:
            page = metric.get("url")
            if page and _is_excluded_page(page):
                return safe_jsonify({"status": "ignored"})
        ic(data_metric)
        metric_model = MetricModel.from_documents(data_metric)
        # Convertirlos en dicts listos para MongoDB (timestamp como datetime real)
        docs = [m.to_dict() for m in metric_model]
        ic(docs)
        MetricsEndpoints.service.create_metrics(metric=docs)
        return safe_jsonify({"status": "stored"})
    @staticmethod
    @jwt_admin_required
    def summary(user):
        minutes = int(request.args.get("minutes", 30))
        resultado = MetricsEndpoints.service.get_summary(minutes)
        ic(resultado)
        return jsonify(resultado)
    @staticmethod
    @limiter.limit("3 per minute")
    @jwt_admin_required
    def timeline(user):
        category = request.args.get("category", "")
        categories = [c.strip() for c in category.split(",") if c.strip()]
        # Validar categorías por defecto
        if not categories:
            categories = ["apiresponsetime", "webvitals"]
        interval = request.args.get("interval", "hour")
        limit = int(request.args.get("limit", 24))
        role = request.args.get("role", "User")
        resultado = MetricsEndpoints.service.get_timeline(categories, interval, limit, role)
        ic(resultado)
        return jsonify(resultado)
    @staticmethod
    @jwt_admin_required
    def alerts(user):
        minutes = int(request.args.get("minutes", 60))
        return jsonify(MetricsEndpoints.service.get_recent_alerts(minutes))


# -----------------------------
# Register routes
# -----------------------------
metrics_bp.add_url_rule(
    "/collect-web-vitals", view_func=MetricsEndpoints.collect_webvitals, methods=["POST"], endpoint="collect_webvitals"
)
metrics_bp.add_url_rule(
    "/collect-api", view_func=MetricsEndpoints.collect_api, methods=["POST"], endpoint="collect_api"
)
metrics_bp.add_url_rule(
    "/summary", view_func=MetricsEndpoints.summary, methods=["GET"], endpoint="metrics_summary"
)
metrics_bp.add_url_rule(
    "/timeline", view_func=MetricsEndpoints.timeline, methods=["GET"], endpoint="metrics_timeline"
)
metrics_bp.add_url_rule(
    "/alerts", view_func=MetricsEndpoints.alerts, methods=["GET"], endpoint="metrics_alerts"
)
