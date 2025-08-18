from datetime import datetime, timezone


from app.model.audit_session import AuditLog
from app.utils.db_mongo import MongoDatabase


class AuditLogDAO:
    def __init__(self):
        self.db = MongoDatabase()
        self.session_audit = "session_audit"

    def insert_logs_audit(self, audit_log: AuditLog, context: str = "") -> dict:
        return self.db.insert_with_log(collection=self.session_audit, document=audit_log.to_dict(), context=context)

    def get_logs_audit(self, **kwargs) -> dict:

        user_id = kwargs.get("user_id")
        event_type = kwargs.get("event_type")
        start = kwargs.get("start")
        end = kwargs.get("end")
        page = kwargs.get("page", 1)
        limit = kwargs.get("limit", 10)

        time_filter = {}

        # Filtrar por usuario solo si se especifica
        if user_id:
            time_filter["user_id"] = str(user_id)

        # Filtrar por tipo de evento si se especifica
        if event_type:
            time_filter["event_type"] = event_type

        # Filtrar por rango de fechas si se especifica
        if start or end:
            time_filter["timestamp"] = {}
            if start:
                time_filter["timestamp"]["$gte"] = datetime.fromtimestamp(float(start), tz=timezone.utc)
            if end:
                time_filter["timestamp"]["$lte"] = datetime.fromtimestamp(float(end), tz=timezone.utc)

        skip = (page - 1) * limit

        pipeline = [
            {"$match": time_filter},
            {"$sort": {"timestamp": -1}},
            {
                "$facet": {
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
                            "timestamp": 1
                        }}
                    ],
                    "totalCount": [
                        {"$count": "count"}
                    ]
                }
            }
        ]

        result = list(self.db.aggregate(self.session_audit, pipeline=pipeline))
        data = result[0] if result else {"data": [], "totalCount": []}

        # Convertir timestamps en ISO8601
        for log in data["data"]:
            if isinstance(log.get("timestamp"), datetime):
                log["timestamp"] = log["timestamp"].isoformat()

        total_count = data["totalCount"][0]["count"] if data["totalCount"] else 0

        return {
            "logs": data["data"],
            "total_count": total_count,
            "page": page,
            "limit": limit
        }
