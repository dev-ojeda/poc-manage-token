import datetime
from typing import Dict, Any

from app.dao.metrics_dao import MetricsDAO
from app.model.metrics_model import MetricModel


class MetricService:
    """
    Servicio para manejar métricas de performance y alertas asociadas.
    """

    def __init__(self):
        self.dao_metric = MetricsDAO()

    # --------------------------
    # CRUD de métricas
    # --------------------------
    def create_metrics(self, metric: list[dict]) -> dict[str, Any]:
        """
        Inserta una nueva métrica en la base de datos.
        """
        return self.dao_metric.create_metric(metric=metric)

    # --------------------------
    # Resúmenes de métricas
    # --------------------------
    def get_summary(self, minutes: int = 30) -> dict:
        """
        Retorna un resumen global + por página de los últimos N minutos.
        """
        return self.dao_metric.summary_by_endpoint(minutes=minutes)

    # --------------------------
    # Timeline (series temporales)
    # --------------------------
    def get_timeline(
        self,
        category: list[str],
        interval: str,
        limit: int,
        role: str = None
    ) -> list[dict[str, Any]]:
        """
        Retorna timeline agregado para gráficos.
        """
        return self.dao_metric.aggregate_timeline_dict(
            categories=category,
            interval=interval,
            limit=limit,
            role=role
        )

    # --------------------------
    # Alertas recientes
    # --------------------------
    def get_recent_alerts(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Devuelve las alertas ocurridas en los últimos N minutos.
        """
        cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(minutes=minutes)
        return self.dao_metric.find_alerts_since(cutoff)
