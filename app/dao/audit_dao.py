import datetime
from datetime import timezone
from icecream import ic
from pymongo.cursor import SON


from app.model import AuditLogModel
from app.utils.db_mongo import MongoDatabase


class AuditLogDAO:
    def __init__(self):
        self.db = MongoDatabase()
        self.session_audit = "session_audit"

    def insert_logs_audit(self, audit_log: AuditLogModel, context: str = "") -> dict:
        return self.db.insert_with_log(collection=self.session_audit, document=audit_log.to_dict(), context=context)

    def get_logs_audit(self, **kwargs) -> dict:
        """
        Obtiene logs de auditoría con filtros opcionales, paginación y ordenamiento.
        Soporta:
        - user_id
        - event_type
        - start / end (datetime)
        - page, limit
        - sort_by (timestamp | event_type | user_id | ip_address)
        - direction (asc | desc)
        """
        user_id = kwargs.get("user_id")
        event_type = kwargs.get("event_type")
        start = kwargs.get("start")
        end = kwargs.get("end")
        page = int(kwargs.get("page", 1))
        limit = int(kwargs.get("limit", 10))
        skip = (page - 1) * limit

        # --- Filtros ---
        filters = {}
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

        ic("FILTERS", filters)


        # --- Pipeline ---
        pipeline = [
            {"$match": filters},
            # Campo dinámico "changes"
            {
                "$addFields": {
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
                                        "cond": {
                                            "$ne": [
                                                {"$ifNull": ["$$field.v.old", None]},
                                                {"$ifNull": ["$$field.v.new", None]}
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },

            # Paginación con $facet
            {
                "$facet": {
                    "data": [
                        {"$skip": skip},
                        {"$limit": limit},
                        {
                            "$project": {
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
                            }
                        }
                    ],
                    "totalCount": [
                        {"$count": "count"}
                    ]
                }
            }
        ]

        result = list(self.db.aggregate(collection=self.session_audit, pipeline=pipeline))
        data = result[0] if result else {"data": [], "totalCount": []}

        logs = data.get("data", [])
        # Normalizar timestamps a ISO
        for log in logs:
            if isinstance(log.get("timestamp"), datetime.datetime):
                log["timestamp"] = log["timestamp"].isoformat()

        total_count = data.get("totalCount", [{}])
        total_count = total_count[0].get("count", 0) if total_count else 0

        return {
            "logs": logs,
            "total_count": total_count,
            "page": page,
            "limit": limit
        }

    def get_all_logs_audit(self) -> dict:
    
        # --- Filtros ---
        filters = {}
        # --- Pipeline ---
        pipeline = [
            {"$match": filters},
            {"$sort": SON([("timestamp", -1)])},
            {
                "$project": {
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
                }
            }
        ]

        # pipeline.append({
        #     "$project": {
        #         "_id": 0,
        #         "session_id": 1,
        #         "user_id": 1,
        #         "event_type": 1,
        #         "old_value": 1,
        #         "new_value": 1,
        #         "ip_address": 1,
        #         "user_agent": 1,
        #         "timestamp": 1,
        #         "changes": 1,
        #     }
        # })
      

        result = list(self.db.aggregate(collection=self.session_audit, pipeline=pipeline))
        logs = result
        total_count = len(logs)
        # Normalizar timestamps a ISO
        for log in logs:
            if isinstance(log.get("timestamp"), datetime.datetime):
                log["timestamp"] = log["timestamp"].isoformat()

        return {
            "logs": logs,
            "total_count": total_count
        }



    def insert_event_audit(self, previous_session: dict, **kwargs) -> dict:
        audit_events = []
        ip_changed = previous_session.get("ip_address") != kwargs["ip_address"]
        ua_changed = previous_session.get("user_agent") != kwargs["user_agent"]

        if ip_changed or ua_changed:
            audit_events = {
                 "username": kwargs["username"],
                 "device_id": kwargs["device_id"],
                 "timestamp": datetime.datetime.now(tz=timezone.utc),
                 "old_ip_address": previous_session.get("ip_address"),
                 "new_ip_address": kwargs["ip_address"],
                 "old_user_agent": previous_session.get("user_agent"),
                 "new_user_agent": kwargs["user_agent"],
                 "reason": []
            }
            if ip_changed:
                audit_events["reason"].append("ip_changed")
            if ua_changed:
                audit_events["reason"].append("user_agent_changed")
            

        return self.db.insert_with_log(self.session_audit, audit_events,context="Evento Auditoria")