from bson.objectid import ObjectId
from datetime import datetime

from app.utils.db_mongo import MongoDatabase

class PerformanceMetricsDAO:
    def __init__(self,):
        self.db = MongoDatabase()
        self.collection = "performance_metrics"

    # Insertar un nuevo documento
    def insert_metric(self, metric: dict) -> str:
        result = self.db.insert_one(collection=self.collection, document=metric)
        return str(result.inserted_id)

    # Buscar métricas por URL
    def find_by_url(self, url: str) -> list:
        return list(self.db.find(collection=self.collection,query={"url": url}))

    # Buscar métricas por rango de fechas
    def find_by_date_range(self, start: datetime, end: datetime) -> list:
        query = {"timestamp": {"$gte": start, "$lte": end}}
        return list(self.db.find(collection=self.collection,query=query))

    # Actualizar métricas por ID
    def update_metric(self, identificador: str, updated_fields: dict) -> int:
        result = self.db.update_one(self.collection,
            {"_id": ObjectId(identificador)},
            {"$set": updated_fields},
            upsert=False
        )
        return result.modified_count

    # Borrar métricas por ID
    def delete_metric(self, identificador: str) -> int:
        result = self.db.delete_one(self.collection,{"_id": ObjectId(identificador)})
        return result.deleted_count
