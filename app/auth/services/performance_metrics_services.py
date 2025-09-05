import datetime
from datetime import timezone

from app.dao.performance_metrics_dao import PerformanceMetricsDAO


class PerformanceMetricsService:
    def __init__(self):
        self.dao = PerformanceMetricsDAO()

    # Validación de métricas básicas
    def validate_metrics(self, metrics: dict):
        if not isinstance(metrics, dict):
            raise ValueError("Metrics debe ser un diccionario")
        
        for key in ["LCP", "INP", "FCP"]:
            if key not in metrics or metrics[key] < 0:
                raise ValueError(f"{key} debe ser un número positivo")
        
        if "CLS" not in metrics or not (0 <= metrics["CLS"] <= 1):
            raise ValueError("CLS debe estar entre 0 y 1")

    # Crear nueva métrica
    def create_metric(self, url: str, metrics: dict, device: dict, user_id: str = None):
        self.validate_metrics(metrics)
        document = {
            "url": url,
            "timestamp": datetime.datetime.now(tz=timezone.utc),
            "metrics": metrics,
            "device": device,
            "user_id": user_id
        }
        return self.dao.insert_metric(document)

    # Obtener métricas por URL
    def get_metrics_by_url(self, url: str):
        return self.dao.find_by_url(url)

    # Obtener métricas por rango de fechas
    def get_metrics_by_date_range(self, start: datetime, end: datetime):
        return self.dao.find_by_date_range(start, end)

    # Actualizar métricas
    def update_metric(self, metric_id: str, updated_metrics: dict):
        self.validate_metrics(updated_metrics)
        return self.dao.update_metric(metric_id, {"metrics": updated_metrics})

    # Borrar métricas
    def delete_metric(self, metric_id: str):
        return self.dao.delete_metric(metric_id)
