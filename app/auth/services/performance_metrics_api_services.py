import datetime
import logging
from typing import Dict, List

from icecream import ic

from app.dao.performancemetricsapi_dao import PerformanceMetricsApiDAO
from app.dao.alerts_dao import AlertsDao
from app.model.performance_metrics_api_model import PerformanceMetricApiModel
from app.model.alert_model import AlertModel

ALERT_THRESHOLDS = {
    "LCP": 2500,
    "FID": 100,
    "CLS": 0.1,
    "INP": 200,
    "TTFB": 500,
    "apiResponseTime": 1000,
}


class PerformanceMetricsApiService:
    """
    Servicio para manejar métricas de API y alertas asociadas.
    """

    def __init__(self):
        self.dao_performance = PerformanceMetricsApiDAO()
        self.dao_alert = AlertsDao()
        self.model_class = PerformanceMetricApiModel

    # --------------------------
    # Crear métricas y alertas
    # --------------------------
    def create_metric_api(self, metric: PerformanceMetricApiModel) -> Dict:
        """
        Inserta la métrica y evalúa alertas asociadas.
        """
        result = self._save_metric(metric)
        ic(result)
        self._evaluate_alert(metric)

        return result

    def _save_metric(self, metric: PerformanceMetricApiModel) -> Dict:
        """
        Inserta la métrica en la base de datos.
        """
        result = self.dao_performance.create(metric=metric)
        return result

    def _evaluate_alert(self, metric: PerformanceMetricApiModel):
        """
        Evalúa si la métrica supera el umbral y genera alerta.
        """
        threshold = ALERT_THRESHOLDS.get(metric.type)
        if not threshold or metric.value <= threshold:
            return

        severity = "critical" if metric.value > 1.5 * threshold else "warning"
        alert = AlertModel(
            metric=metric.type,
            severity=severity,
            value=metric.value,
            threshold=threshold,
            page=metric.url,
            ts=metric.ts or datetime.datetime.now()
        )
        self.dao_alert.create(alert=alert, context="Crear Alerta")
        logging.warning(
            f"🚨 ALERT: {alert.metric}={alert.value} > {alert.threshold} ({alert.severity}) en {alert.page}"
        )
        ic(f"🚨 ALERT: {alert.metric}={alert.value} > {alert.threshold} ({alert.severity}) en {alert.page}")

    # --------------------------
    # Consultas de métricas
    # --------------------------
    def get_metrics_timeline(
        self,
        role: str,
        category: str,
        interval: str = "hour",
        limit: int = 100,
        group_by_endpoint: bool = False
    ) -> Dict[str, List]:
        return self.dao_performance.get_metrics_timeline(
            role=role,
            category=category,
            interval=interval,
            limit=limit,
            group_by_endpoint=group_by_endpoint
        )

    def get_metrics_by_date_range(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> List[Dict]:
        return self.dao_performance.find_by_date_range(start=start, end=end)

    # --------------------------
    # Alertas recientes
    # --------------------------
    def get_alerts(self, last_hours: int = 1) -> Dict:
        minutes = last_hours * 60
        return self.dao_performance.get_alerts_recent(minutes=minutes)

    # --------------------------
    # Operaciones de mantenimiento
    # --------------------------
    def update_metric(self, metric_id: str, updated_metrics: Dict) -> Dict:
        self.validate_metrics(updated_metrics)
        return self.dao_performance.update_metric(metric_id, {"metrics": updated_metrics})

    def delete_metric(self, metric_id: str) -> Dict:
        return self.dao_performance.delete_metric(metric_id)

    # --------------------------
    # Validación de métricas
    # --------------------------
    @staticmethod
    def validate_metrics(metrics: Dict):
        if not metrics:
            raise ValueError("No se proporcionaron métricas para actualizar.")
        # Aquí puedes agregar validaciones adicionales según tus reglas de negocio
