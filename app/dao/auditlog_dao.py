# audit_log_dao.py
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.model.audit_session_model import AuditLogModel
from app.core.base_dao import BaseDAO
from app.logging_config import get_logger


class AuditLogDAO(BaseDAO):
    COLLECTION = "session_audit"

    def __init__(self, db=None, logger=None):
        super().__init__(db=db, collection_name=self.COLLECTION)
        self.logger = logger or get_logger("AuditLogDAO")

    def _now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    # -------------------------------
    # Insertar log de auditoría
    # -------------------------------
    def insert_logs_audit(self, audit_log: AuditLogModel, *, context: str = "Insert Audit Log") -> dict:
        return self.insert_one(audit_log.to_dict(), context=context)

    # -------------------------------
    # Obtener logs con filtros y paginación
    # -------------------------------
    def get_logs_audit(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        page: int = 1,
        limit: int = 10,
        sort_by: str = "timestamp",
        direction: str = "desc",
        *,
        context: str = "Get Logs Audit"
    ) -> Dict[str, Any]:
        skip = (page - 1) * limit
        filters: Dict[str, Any] = {}

        if user_id:
            filters["user_id"] = user_id
        if event_type:
            filters["event_type"] = event_type
        if start or end:
            filters["timestamp"] = {}
            if start:
                filters["timestamp"]["$gte"] = start
            if end:
                filters["timestamp"]["$lte"] = end

        pipeline = [
            {"$match": filters},
            {"$addFields": {
                "changes": {
                    "$let": {
                        "vars": {
                            "allFields": {
                                "$mergeObjects": [
                                    {"old_value": {"old": "$old_value", "new": "$new_value"}},
                                    {"ip_address": {"old": "$old_ip", "new": "$ip_address"}},
                                    {"user_agent": {"old": "$old_user_agent", "new": "$user_agent"}}
                                ]
                            }
                        },
                        "in": {
                            "$arrayToObject": {
                                "$filter": {
                                    "input": {"$objectToArray": "$$allFields"},
                                    "as": "field",
                                    "cond": {"$ne": [
                                        {"$ifNull": ["$$field.v.old", None]},
                                        {"$ifNull": ["$$field.v.new", None]}
                                    ]}
                                }
                            }
                        }
                    }
                }
            }},
            {"$sort": {sort_by: -1 if direction == "desc" else 1}},
            {"$skip": skip},
            {"$limit": limit},
        ]

        result = self.aggregate(pipeline, context=context)
        logs = result.get("data", [])

        # Normalizar timestamps
        for log in logs:
            if isinstance(log.get("timestamp"), datetime):
                log["timestamp"] = log["timestamp"].isoformat()

        total_count = self.count(filters, context=f"{context} Count").get("data", {}).get("count", 0)

        return {
            "logs": logs,
            "total_count": total_count,
            "page": page,
            "limit": limit,
        }

    # -------------------------------
    # Obtener todos los logs de auditoría
    # -------------------------------
    def get_all_logs_audit(self, *, context: str = "Get All Audit Logs") -> Dict[str, Any]:
        pipeline = [
            {"$sort": {"timestamp": -1}},
        ]

        result = self.aggregate(pipeline, context=context)
        logs = result.get("data", [])

        for log in logs:
            if isinstance(log.get("timestamp"), datetime):
                log["timestamp"] = log["timestamp"].isoformat()

        total_count = self.count({}, context=f"{context} Count").get("data", {}).get("count", 0)

        return {
            "logs": logs,
            "total_count": total_count,
            "success": result.get("success", False),
            "context": context
        }

    # -------------------------------
    # Insertar evento de auditoría de sesión
    # -------------------------------
    def insert_event_audit(self, previous_session: dict, **kwargs) -> dict:
        """
        Inserta un evento de auditoría si cambian IP o user_agent.
        """
        ip_changed = previous_session.get("ip_address") != kwargs["ip_address"]
        ua_changed = previous_session.get("user_agent") != kwargs["user_agent"]["browser"]

        if not (ip_changed or ua_changed):
            return {"success": False, "message": "No changes detected"}

        audit_event = {
            "username": kwargs["username"],
            "device_id": kwargs["device_id"],
            "timestamp": self._now(),
            "old_ip_address": previous_session.get("ip_address"),
            "new_ip_address": kwargs["ip_address"],
            "old_user_agent": previous_session.get("user_agent"),
            "new_user_agent":kwargs["user_agent"]["browser"],
            "reason": []
        }
        if ip_changed:
            audit_event["reason"].append("ip_changed")
        if ua_changed:
            audit_event["reason"].append("user_agent_changed")

        return self.insert_one(audit_event, context="Evento Auditoria")
