import logging
import datetime
from datetime import timezone
from typing import Optional, Dict, Any, List

from pymongo import ASCENDING
from pymongo.cursor import SON

from app.core.base_dao import BaseDAO
from app.model.alert_model import AlertModel
from app.model.performance_metrics_api_model import ALERT_THRESHOLDS, PerformanceMetricApiModel


class PerformanceMetricsApiDAO(BaseDAO):
    def __init__(self, db=None):
        super().__init__(db=db, collection_name="performance_metrics_api")
        self.col_alerts = "alerts"

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(tz=timezone.utc)

    # ---------- Insertar Performance métrica ----------
    def create(self, metric: PerformanceMetricApiModel) -> Dict[str, Any] | None:
        """
        Inserta una métrica y genera alerta si supera un umbral.
        """
        try:
            document = metric.to_dict()
            result = self.insert_with_log(document, context="Insertar Métrica API")
            if not result.get("success"):
                return result

            alert_info: Optional[Dict[str, Any]] = None
            threshold = ALERT_THRESHOLDS.get(metric.type)
            if threshold and metric.value > threshold:
                severity = "critical" if metric.value > 1.5 * threshold else "warning"
                alert = AlertModel(
                    metric=metric.type,
                    severity=severity,
                    value=metric.value,
                    threshold=threshold,
                    page=metric.url,
                    ts=metric.ts or self._now()
                )
                alert_result = self.update_with_log(
                    query={"metric": alert.metric, "page": alert.page, "ts": alert.ts},
                    update={"$setOnInsert": alert.to_dict()},
                    upsert=True,
                    context=f"Insertar Alerta API ({severity.upper()})"
                )
                alert_info = alert_result

            return {"metric": result, "alert": alert_info}

        except Exception as e:
            logging.getLogger(__name__).error("Error creando métrica", exc_info=e)
            return None

    # ---------- Consultar métricas endpoint timeline ----------
    def get_metrics_timeline(
        self,
        role: str,
        category: str,
        interval: str = "hour",
        limit: int = 100,
        group_by_endpoint: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:

        if interval not in ["minute", "hour", "day"]:
            interval = "hour"

        group_id = {"bucket": {"$dateTrunc": {"date": "$ts", "unit": interval}}}
        if group_by_endpoint and category == "endpoint":
            group_id.update({"url": "$url", "method": "$method"})

        pipeline = [
            {"$match": {"role": role, "category": category}},
            {"$group": {
                "_id": group_id,
                "avg": {"$avg": "$value"},
                "min": {"$min": "$value"},
                "max": {"$max": "$value"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id.bucket": ASCENDING}},
            {"$limit": limit},
        ]

        result = self.aggregate(pipeline=pipeline)
        series: List[Dict[str, Any]] = []

        for r in result["data"]:
            metric_entry = PerformanceMetricApiModel(
                type="apiResponseTime",  # se puede parametrizar si se requiere
                category=category,
                value=r.get("avg", 0),
                url=r["_id"].get("url") if group_by_endpoint else None,
                method=r["_id"].get("method") if group_by_endpoint else None,
                role=role,
                ts=r["_id"]["bucket"]
            )
            entry = metric_entry.to_dict()
            entry.update({
                "avg": round(r.get("avg", 0), 2),
                "min": r.get("min"),
                "max": r.get("max"),
                "count": r.get("count")
            })
            series.append(entry)

        return {"metrics": series}

    # ---------- Consultar alertas recientes ----------
    def get_alerts_recent(self, minutes: int = 60) -> Dict[str, Any]:
        since = self._now() - datetime.timedelta(minutes=minutes)
        match_filter = {"ts": {"$gte": since}}

        pipeline = [
            {"$match": match_filter},
            {"$sort": SON([("ts", -1)])},
            {"$project": {
                "_id": 1, "metric": 1, "value": 1, "severity": 1, "page": 1, "ts": 1
            }}
        ]

        try:
            result = self.db.aggregate(collection=self.col_alerts, pipeline=pipeline).get("data", [])
        except Exception as e:
            logging.getLogger(__name__).error("Error obteniendo alertas recientes", exc_info=e)
            return {"alerts": [], "total_count": 0}

        alerts: List[Dict[str, Any]] = [
            AlertModel(
                metric=a["metric"],
                severity=a["severity"],
                value=a["value"],
                threshold=a.get("threshold", 0),
                page=a.get("page"),
                ts=a["ts"]
            ).to_dict(normalize_ts=True) for a in result
        ]

        return {"alerts": alerts, "total_count": len(alerts)}
