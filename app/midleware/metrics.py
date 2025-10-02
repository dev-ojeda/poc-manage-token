import time
import logging
from flask import request, g
from icecream import ic
from app.model.performance_metrics_api_model import PerformanceMetricApiModel
from app.auth.services.performance_metrics_api_services import PerformanceMetricsApiService

IGNORED_PATHS = [
    "/", 
    "/health", 
    "/static", 
    "/favicon.ico",
    "/api/metrics/timeline", 
    "/api/metrics/collect-metrics", 
    "/dashboard",
    "/.well-known/appspecific/com.chrome.devtools.json"
]

def is_ignored(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in IGNORED_PATHS)

def init_metrics(app):
    perf_service = PerformanceMetricsApiService()

    @app.after_request
    def save_metrics(response):
        try:
            if hasattr(g, "start_time") and not is_ignored(request.path):
                duration = (time.perf_counter() - g.start_time) * 1000
                perf_model = PerformanceMetricApiModel(
                    type="apiResponseTime",
                    category="endpoint",
                    value=round(duration, 2),
                    url=request.path,
                    method=request.method,
                    status=str(response.status_code),
                )
                result = perf_service.create_metric_api(metric=perf_model)
                if not result["metric"]["success"]:
                    response.headers["X-Error-Api"] = result.get("error")

                # Logging de acceso
                ip = request.headers.get("X-Forwarded-For", request.remote_addr)
                ua = request.user_agent.string[:120]
                logging.info(f"⏱ {request.method} {request.path} {response.status_code} - {duration:.2f} ms | {ip} | {ua}")
        except Exception as e:
            logging.error(f"Error guardando PerformanceMetric: {e}", exc_info=True)
            ic(f"Error guardando PerformanceMetric: {e}")
            response.headers["X-Error-API"] = str(e)
        return response

