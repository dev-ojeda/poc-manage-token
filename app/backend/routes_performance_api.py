import datetime
from flask import Blueprint, jsonify, request
from app.auth.services.metrics_service import MetricService
from app.auth.services.performance_metrics_api_services import PerformanceMetricsApiService
from app.midleware.jwt_guard import admin_required
from app.model.metrics_model import MetricModel
from app.model.performance_metrics_api_model import PerformanceMetricApiModel
from icecream import ic

performance_bp = Blueprint("performance_bp", __name__)
# ============================================================
# Helpers
# ============================================================
def safe_jsonify(data, status: int = 200):
    """Envuelve jsonify con manejo de errores de conexión."""
    try:
        resp = jsonify(data)
        resp.status_code = status
        return resp
    except GeneratorExit:
        ic("Cliente cerró la conexión antes de recibir la respuesta")
        return "", 499  # 499 Client Closed Request (no estándar, solo informativo)
    except Exception as e:
        ic(f"Error al generar respuesta JSON: {e}", exc_info=e)
        return jsonify({"error": "Internal server error"}), 500

# ---------- Insertar Métrica ----------
# ---------- Insertar Métrica ----------
@performance_bp.route("/metrics/create-metrics", methods=["POST"])
@admin_required
def create_metric(user):
    metrics_services = MetricService()
    if not request.is_json:
        return jsonify({"msg": "Content-Type debe ser application/json", "code": "INVALID_JSON"}), 400
    
    data = request.get_json()
    metric_model = MetricModel(
        name=data.get("name"),
        value=float(data.get("value", 0)),
        category=data.get("category", "endpoint"),
        role=data.get("role", "User"),
        page=data.get("page"),
        url=data.get("url"),
        os=data.get("os"),
        browser=data.get("browser"),
        metric_id=data.get("metric_id"),
        timestamp=datetime.datetime.now(tz=datetime.timezone.utc)
    )
    metric_id = metrics_services.create_metrics(metric=metric_model)
    if metric_id.get("success"):
        return safe_jsonify(metric_id)
    return safe_jsonify(metric_id, 400)

# ---------- Timeline ----------
# @performance_bp.route("/metrics/timeline", methods=["GET"])
# @admin_required
# def get_metrics_timeline(user):
#     performance_api_service=PerformanceMetricsApiService()
#     try:
#         role = request.args.get("role", "User")
#         category = request.args.get("category", "endpoint")
#         interval = request.args.get("interval", "hour")
#         limit = request.args.get("limit", type=int, default=50)
#         group_by_endpoint = request.args.get("group_by_endpoint", "true").lower() == "true"

#         results = performance_api_service.get_metrics_timeline(
#             role=role,
#             category=category,
#             interval=interval,
#             limit=limit,
#             group_by_endpoint=group_by_endpoint,
#         )
#         ic(results)
#         return jsonify(results)
#     except Exception as e:
#         ic("Error en /metrics/timeline", exc_info=e)
#         return safe_jsonify({"status": "error", "message": str(e)}, 500)

# ---------- Alertas ----------
@performance_bp.route("/metrics/alerts", methods=["GET"])
@admin_required
def get_alerts(user):
    metrics_services = MetricService()
    try:
        last_hours = request.args.get("last_hours", type=int, default=24)
        alerts = metrics_services.get_recent_alerts(minutes=last_hours * 60)
        return jsonify(alerts)
    except Exception as e:
        ic("Error en /metrics/alerts", exc_info=e)
        return safe_jsonify({"status": "error", "message": str(e)}, 500)

# ---------- Timeline combinado ----------
@performance_bp.route("/metrics/timelines", methods=["GET"])
@admin_required
def timeline(user):
    """
    Devuelve en una sola respuesta:
      - metrics: serie temporal agrupada por endpoint/intervalo
      - alerts: alertas recientes
    """
    performance_api_service = PerformanceMetricsApiService()
    try:
        role = request.args.get("role", "User")
        category = request.args.get("category", "endpoint")
        interval = request.args.get("interval", "hour")
        limit = request.args.get("limit", type=int, default=50)
        group_by_endpoint = request.args.get("group_by_endpoint", "true").lower() == "true"

        metrics = performance_api_service.get_metrics_timeline(
            role=role,
            category=category,
            interval=interval,
            limit=limit,
            group_by_endpoint=group_by_endpoint,
        )
        alerts = performance_api_service.get_alerts(last_hours=24)

        # ✅ Estructura clara, sin tuplas que rompan jsonify
        return jsonify({
            "metrics": metrics,
            "alerts": alerts
        })
    except Exception as e:
        ic("Error en /metrics/timelines", exc_info=e)
        return safe_jsonify({"status": "error", "message": str(e)}, 500)

# =========================
# Timelines combinadas (para tu JS: metrics + alerts)
# =========================
@performance_bp.route("/metrics/combined/timelines", methods=["GET"])
@admin_required
def get_combined_timelines(user):
    """
    Devuelve métricas + alertas combinadas
    Usado en el frontend en fetchTimeline()
    """
    metrics_services = MetricService()
    role = request.args.get("role", "User")
    category = request.args.get("category", "endpoint")
    interval = request.args.get("interval", "hour")
    limit = request.args.get("limit", type=int, default=50)
    group_by_endpoint = request.args.get("group_by_endpoint", "true").lower() == "true"

    metrics = metrics_services.get_timeline(role=role, category=category, interval=interval, limit=limit, group_by_endpoint=group_by_endpoint)
    alerts = metrics_services.get_recent_alerts(minutes=24 * 60)

    return jsonify({
        "metrics": metrics,
        "alerts": alerts
    })