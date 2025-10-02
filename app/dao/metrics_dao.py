import datetime
from datetime import timedelta, timezone
from typing import Any, Optional, List
from icecream import ic
from pymongo import DESCENDING
from pymongo.cursor import SON

from app.dao.base_dao import BaseDAO
from app.model.alert_model import AlertModel
from app.model.metrics_model import MetricModel
from app.utils.percentiles import PERCENTILES_CONFIG
from app.utils.thresholds import THRESHOLDS


class MetricsDAO(BaseDAO):
    METRICS_COLLECTION = "metrics"
    ALERTS_COLLECTION = "alerts"
    ALERT_COOLDOWN_MINUTES = 5

    def __init__(self, db=None):
        super().__init__(db=db, collection_name=self.METRICS_COLLECTION)
        self.dao_alert = BaseDAO(db=db, collection_name=self.ALERTS_COLLECTION)
        self._thresholds = THRESHOLDS
        self._percentiles_config = PERCENTILES_CONFIG
        self._alert_cache: dict[tuple[str, str], datetime.datetime] = {}

    # -------------------------------
    # Helpers internos
    # -------------------------------
    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(tz=timezone.utc)

    @property
    def thresholds(self) -> dict:
        return self._thresholds

    @property
    def percentiles_config(self) -> dict:
        return self._percentiles_config

    # ---------------- Helpers ----------------
    def _build_query_filter(self, minutes: Optional[int] = None) -> dict:
        return {"timestamp": {"$gte": self._now() - timedelta(minutes=minutes)}} if minutes else {}

    def _group_local(self, docs: List[dict], group_by: str = "page") -> dict:
        grouped: dict[str, dict[str, list[float]]] = {}
        for doc in docs:
            key = doc.get(group_by, "GLOBAL")
            grouped.setdefault(key, {})
            name = doc.get("name")
            grouped[key].setdefault(name, [])
            grouped[key][name].append(doc.get("value", 0.0))
        return grouped
    # ==============================
    # Helpers
    # ==============================
    def _build_date_trunc(self, unit: str):
        """
        Retorna expresión de truncado de fechas compatible
        con MongoDB >= 5.0 ($dateTrunc) o < 5.0 ($dateFromParts).
        """
        try:
            # Intentamos usar $dateTrunc (MongoDB >= 5.0)
            return {
                "$dateTrunc": {
                    "date": "$timestamp",
                    "unit": unit,
                    "binSize": 1,
                    "timezone": "UTC",
                }
            }
        except Exception:
            # Fallback MongoDB 4.4 o menos
            parts = {
                "year": {"$year": "$timestamp"},
                "month": {"$month": "$timestamp"},
                "day": {"$dayOfMonth": "$timestamp"},
            }
            if unit in ("hour", "minute"):
                parts["hour"] = {"$hour": "$timestamp"}
            if unit == "minute":
                parts["minute"] = {"$minute": "$timestamp"}

            return {"$dateFromParts": parts}
    # -------------------------------
    # CRUD Básico
    # -------------------------------
    # ---------------- CRUD ----------------
    def create_metric(self, metric: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """Inserta métrica y genera alerta si supera threshold"""
        try:
            # Convertirlos en dicts listos para MongoDB (timestamp como datetime real)
            result = self.insert_many(metric, context="Insertar Métrica API")
            if not result.get("success"):
                return result

            # Validar thresholds por cada métrica
            for m in metric:
                category = m.get("category")
                if category not in self._thresholds:
                    continue
                name = m.get("name", "UNKNOWN")
                threshold = self._thresholds[category].get(name)

                if threshold is not None and m.get("value", 0) > threshold:
                    self.add_alert(
                        page=m.get("url", "N/A"),
                        name=name,
                        value=m.get("value", 0),
                        threshold=threshold,
                        percentile_key="N/A",
                        samples=1
                    )

            return result
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Error creando métrica", exc_info=e)
            return None

    def find_metrics(
        self,
        query: Optional[dict] = None,
        projection: Optional[dict] = None,
        sort: Optional[list] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        coll = self.db._get_collection(self.collection_name)
        cursor = coll.find(query or {}, projection or {})
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    # -------------------------------
    # Resúmenes de métricas
    # -------------------------------

    def summary_by_page(self, minutes: Optional[int] = None) -> dict:
        docs = self.find_metrics(query={},
            projection={
                "_id": 1,
                "name": 1,
                "category": 1,
                "role": 1,
                "value": 1,
                "page": 1,
                "url": 1,
                "os": 1,
                "browser": 1,
                "metric_id": 1,
                "timestamp": 1
            },
            sort=[("timestamp", -1)],
            limit=50)
        grouped = self._group_local(docs, group_by="page")
        summary = dict[str, Any] = {}
        default_thresholds = self._thresholds["default"]

        for page, metrics_dict in grouped.items():
            page_thresholds = self._thresholds.get(page, default_thresholds)
            summary[page] = {}
            for name, values in metrics_dict.items():
                threshold = float(page_thresholds.get(name, default_thresholds.get(name, 0)))
                summary[page][name] = self.summarize_metric(page, name, values, threshold)
        return summary


    def summary_global(self, minutes: Optional[int] = None) -> dict:
        docs = self.find_metrics(query={},
            projection={
                "_id": 1,
                "name": 1,
                "category": 1,
                "role": 1,
                "value": 1,
                "page": 1,
                "url": 1,
                "os": 1,
                "browser": 1,
                "metric_id": 1,
                "timestamp": 1
            },
            sort=[("timestamp", -1)],
            limit=50)
        grouped = self._group_local(docs, group_by="name")
        summary: dict[str, Any] = {}
        default_thresholds = self._thresholds["default"]

        for name, values in grouped.items():
            threshold = float(default_thresholds.get(name, 0))
            summary[name] = self.summarize_metric("GLOBAL", name, values, threshold)
        return summary

    def summary_by_endpoint(self, minutes: Optional[int] = None) -> dict:
        return {"global": self.summary_global(minutes), "pages": self.summary_by_page(minutes)}

    # ---------------- Metric calculations ----------------
    # ejemplo de uso dentro de tu lógica
    def summarize_metric(self, page: str, name: str, values: List[Any], threshold: float) -> dict:
        numeric_values = [float(v) for v in values if isinstance(v, (int, float))]
        if not numeric_values:
            return {"count": 0, **{f"p{int(p*100)}": None for p in self._percentiles_config.get(name, [0.75,0.9,0.95])}, "threshold": threshold}

        sorted_vals = sorted(numeric_values)
        n = len(sorted_vals)

        def percentile(p: float) -> float:
            idx = max(0, min(int(p*n)-1, n-1))
            return sorted_vals[idx]

        percentiles = self._percentiles_config.get(name, [0.75,0.9,0.95])
        return {"count": n, **{f"p{int(p*100)}": percentile(p) for p in percentiles}, "threshold": threshold}

    ## ---------------- Alerts ----------------
    def add_alert(self, page: str, name: str, value: float, threshold: float, percentile_key: str, samples: int):
        now = self._now()
        cache_key = (page, name)
        last_alert = self._alert_cache.get(cache_key)
        if last_alert and (now - last_alert < timedelta(minutes=self.ALERT_COOLDOWN_MINUTES)):
            return

        severity = "critical" if value >= 2*threshold else "warning"
        alert = AlertModel(
            metric=name, severity=severity, value=value, threshold=threshold,
            page=page, ts=now, details={"percentile": percentile_key, "samples": samples}
        )

        try:
            self._alert_dao.insert_one(alert.to_dict(), context="Create Alert")
            self._alert_cache[cache_key] = now
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Error creando alerta", exc_info=e)

    # ---------------- Timeline ----------------
    def aggregate_timeline_dict(
        self,
        categories: List[str],
        interval: str,
        limit: int,
        role: Optional[str] = None
    ) -> dict:
        """
        Retorna un timeline con clave compuesta 'bucket|category|url|metric' para búsquedas rápidas.
        """
        unit_map = {"minute": "minute", "hour": "hour", "day": "day"}
        unit = unit_map.get(interval, "hour")
        group_format = {
            "$dateTrunc": {
                "date": "$timestamp",
                "unit": unit,
                "binSize": 1,
                "timezone": "UTC"
            }
        }

        match_filter = {"category": {"$in": categories}}
        if role:
            match_filter["role"] = role

        pipeline = [
            {"$match": match_filter},
            {"$group": {
                "_id": {
                    "bucket": group_format,
                    "category": "$category",
                    "url": "$url",
                    "metric": "$name"
                },
                "avg": {"$avg": "$value"},
                "min": {"$min": "$value"},
                "max": {"$max": "$value"},
                "count": {"$sum": 1},
            }},
            {"$sort": SON([("_id.bucket", 1)])},
            {"$limit": limit*10}
        ]

        result = self.aggregate(pipeline)
        if isinstance(result, dict):
            result = result.get("data", [])

        buckets: dict[str, dict] = {}
        for r in result:
            bucket_iso = r["_id"]["bucket"].astimezone(timezone.utc).isoformat()
            key = f"{bucket_iso}|{r['_id']['category']}|{r['_id']['url']}|{r['_id']['metric']}"
            buckets[key] = {
                "bucket": bucket_iso,
                "category": r["_id"]["category"],
                "url": r["_id"]["url"],
                "metric": r["_id"]["metric"],
                "avg": float(r["avg"]),
                "min": float(r["min"]),
                "max": float(r["max"]),
                "count": r["count"],
            }
        return buckets

    # -------------------------------
    # Alertas recientes
    # -------------------------------
    def find_alerts_since(self, cutoff: datetime.datetime) -> list[dict]:
        query = {"timestamp": {"$gte": cutoff}}
        return self.find(collection=self.ALERTS_COLLECTION, query=query, sort=[("timestamp", DESCENDING)])
