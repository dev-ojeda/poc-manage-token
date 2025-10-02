import datetime
from datetime import timezone
from typing import Dict, Any
from pymongo.cursor import SON

from app.dao.base_dao import BaseDAO
from app.model.alert_model import AlertModel


class AlertsDao(BaseDAO):
    def __init__(self, db=None):
        super().__init__(db=db, collection_name="alerts")

    # -------------------------------
    # Crear alerta
    # -------------------------------
    def create(self, alert: AlertModel, context: str = "Insert Alert") -> Dict[str, Any]:
        """Inserta una nueva alerta en la colección usando BaseDAO"""
        return self.insert_one(alert.to_dict(), context=context)

    # -------------------------------
    # Obtener alertas recientes
    # -------------------------------
    def get_recent(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Obtiene alertas de los últimos `minutes` minutos.
        Normaliza timestamps a ISO.
        """
        since = datetime.datetime.now(tz=timezone.utc) - datetime.timedelta(minutes=minutes)
        filters = {"timestamp": {"$gte": since}}

        pipeline = [
            {"$match": filters},
            {"$sort": SON([("timestamp", -1)])},
            {"$project": {
                "_id": 1,
                "metric": 1,
                "threshold": 1,
                "severity": 1,
                "page": 1,
                "timestamp": 1
            }}
        ]

        result = self.aggregate(pipeline=pipeline, context="Get Recent Alerts").get("data", [])

        # Normalizar timestamps a ISO
        for alert in result:
            ts = alert.get("timestamp")
            if isinstance(ts, datetime.datetime):
                alert["timestamp"] = ts.isoformat()

        return {
            "alerts": result,
            "total_count": len(result)
        }
