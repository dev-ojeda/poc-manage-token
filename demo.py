# Modify imports for each tutorial as needed.
from datetime import datetime, timezone
from typing import Type
from bson import ObjectId
from icecream import ic, colorize
from pymongo.mongo_client import MongoClient, PyMongoError
from pymongo.server_api import ServerApi
from config import Config



def get_data():
    browser = "Moxilla"
    sistema_operativo = "Windows"
    return {browser,sistema_operativo}

data = get_data()

datos = {"Moxila","Winwos"}
def get_agent(**kwargs):
    salida = [list(value) for value in kwargs.items()]
    listar = list(salida[0][1])
    ic(listar[0])
salida = get_agent(data=data)

ic(salida)
# ic.configureOutput(includeContext=True)
# Replace the placeholder with your connection string.
# client = MongoClient(Config.MONGO_URI_CLUSTER_X509, tls=True, tlsCertificateKeyFile=Config.MONGODB_X509, server_api=ServerApi(version="1", strict=True,deprecation_errors=True))
# agg_db = client["agg_tutorials_db"]        
# person_coll = agg_db["persons"]
# orders_coll = agg_db["orders"]

# def init_db():
#     try:
#       add_aggregate_orders()
#     except PyMongoError as e:
#         ic(f"Error al conectar a MongoDB: {e}")
#         raise
#     finally:
#         client.close()
#         ic("Conexión a MongoDB cerrada")

# def add_aggregate_orders():
#     pipeline = []
#     pipeline.append(
#         {
#             "$match": {
#                 "orderdate": {
#                     "$gte": datetime(2020, 1, 1, 0, 0, 0),
#                     "$lt": datetime(2021, 1, 1, 0, 0, 0),
#                 }
#             }
#         }
#     )
#     pipeline.append({"$sort": {"orderdate": 1}})
#     pipeline.append(
#         {
#             "$group": {
#                 "_id": "$customer_id",
#                 "first_purchase_date": {"$first": "$orderdate"},
#                 "total_value": {"$sum": "$value"},
#                 "total_orders": {"$sum": 1},
#                 "orders": {"$push": {"orderdate": "$orderdate", "value": "$value"}},
#             }
#         }
#     )
#     aggregation_result = orders_coll.aggregate(pipeline)
#     ic(type(aggregation_result))
#     for document in aggregation_result:
#         ic(f"{document}")

# def add_aggregate_person():
#     pipeline = []
#     pipeline.append({"$match": {"vocation": "ENGINEER"}}) #  $match etapa que busque documentos en los que el valor del vocationcampo sea "ENGINEER"
#     pipeline.append({"$sort": {"dateofbirth": -1}}) #  $sort etapa que ordene los documentos en orden descendente por dateofbirthcampo para enumerar primero a las personas más jóvenes
#     pipeline.append({"$limit": 3}) # etapa en la canalización para generar solo los primeros tres documentos en los resultados
#     pipeline.append({"$unset": ["_id", "address"]}) # etapa elimina los campos innecesarios de los documentos de resultados
#     aggregation_result = person_coll.aggregate(pipeline)
#     for document in aggregation_result:
#         ic(f"{document}")

# if __name__ == "__main__":
#     init_db()