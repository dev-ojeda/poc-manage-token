import datetime
from datetime import timezone
from typing import Optional, Dict, Any, List
from bson import SON

from app.model.audit_session_model import AuditLogModel
from app.dao.base_dao import BaseDAO


class AuditLogDAO(BaseDAO):
    def __init__(self, db=None):
        super().__init__(db=db, collection_name="session_audit")

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(tz=timezone.utc)

    # -------------------------------
    # Insertar un log de auditoría
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
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
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
            {"$sort": SON([(sort_by, -1 if direction == "desc" else 1)])},
            {"$facet": {
                "data": [
                    {"$skip": skip},
                    {"$limit": limit},
                    {"$project": {
                        "_id": 0,
                        "session_id": 1,
                        "user_id": 1,
                        "event_type": 1,
                        "old_value": 1,
                        "new_value": 1,
                        "ip_address": 1,
                        "user_agent": 1,
                        "timestamp": 1,
                        "changes": 1
                    }}
                ],
                "totalCount": [{"$count": "count"}]
            }}
        ]

        result = self.aggregate(pipeline, context=context)
        data = result.get("data", [])
        if data:
            data = data[0]
        logs = data.get("data", [])
        total_count = data.get("totalCount", [{}])[0].get("count", 0) if data.get("totalCount") else 0

        # Normalizar timestamps
        for log in logs:
            if isinstance(log.get("timestamp"), datetime.datetime):
                log["timestamp"] = log["timestamp"].isoformat()

        return {
            "logs": logs,
            "total_count": total_count,
            "page": page,
            "limit": limit
        }

    # -------------------------------
    # Obtener todos los logs
    # -------------------------------
    def get_all_logs_audit(self, *, context: str = "Get All Audit Logs") -> Dict[str, Any]:
        pipeline = [
            {"$sort": SON([("timestamp", -1)])},
            {"$project": {
                "_id": 0,
                "session_id": 1,
                "user_id": 1,
                "event_type": 1,
                "old_value": 1,
                "new_value": 1,
                "ip_address": 1,
                "user_agent": 1,
                "timestamp": 1,
                "changes": 1,
            }}
        ]
        result = self.aggregate(pipeline).get("data", [])

        for log in result:
            if isinstance(log.get("timestamp"), datetime.datetime):
                log["timestamp"] = log["timestamp"].isoformat()

        return {
            "logs": result,
            "total_count": len(result)
        }

    # -------------------------------
    # Insertar evento de auditoría de sesión
    # -------------------------------
    def insert_event_audit(self, previous_session: dict, **kwargs) -> dict:
        """
        Inserta un evento de auditoría si IP o user_agent cambian.
        """
        ip_changed = previous_session.get("ip_address") != kwargs.get("ip_address")
        ua_changed = previous_session.get("user_agent") != kwargs.get("browser")

        if not (ip_changed or ua_changed):
            return {"success": False, "message": "No changes detected"}

        audit_event = {
            "username": kwargs.get("username"),
            "device_id": kwargs.get("device_id"),
            "timestamp": self._now(),
            "old_ip_address": previous_session.get("ip_address"),
            "new_ip_address": kwargs.get("ip_address"),
            "old_user_agent": previous_session.get("user_agent"),
            "new_user_agent": kwargs.get("browser"),
            "reason": []
        }
        if ip_changed:
            audit_event["reason"].append("ip_changed")
        if ua_changed:
            audit_event["reason"].append("user_agent_changed")

        return self.insert_one(audit_event, context="Evento Auditoria")
