import datetime
from bson import ObjectId
from icecream import ic
from pymongo.errors import DuplicateKeyError
from app.dao.base_dao import BaseDAO

# Simula tu colección de items
class ItemDAO(BaseDAO):
    COLLECTION = "items"

# Inicializa DAO
dao = ItemDAO()

# Datos de ejemplo
user_id = str(ObjectId())
item_doc = {
    "user_id": ObjectId(user_id),
    "name": "Demo Item",
    "description": "Item de prueba",
    "created_at": datetime.datetime.now(tz=datetime.timezone.utc),
    "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
}

# Función de transacción
def transactional_ops(session=None):
    # 1️⃣ Insertar un item
    insert_res = dao.insert_one(item_doc, context="Insert Demo Item", session=session)
    ic("Insert Result:", insert_res)

    # 2️⃣ Actualizar el item recién insertado
    if insert_res.get("success"):
        item_id = insert_res["data"]["_id"]
        update_res = dao.update_one(
            {"_id": ObjectId(item_id)},
            {"description": "Actualizado en transacción"},
            context="Update Demo Item",
            session=session
        )
        ic("Update Result:", update_res)
    
    # 3️⃣ Hacer un aggregate para contar items por usuario
    pipeline = [
        {"$match": {"user_id": ObjectId(user_id)}},
        {"$group": {"_id": "$user_id", "total": {"$sum": 1}}}
    ]
    aggregate_res = dao.aggregate(pipeline, context="Aggregate Items By User", session=session)
    ic("Aggregate Result:", aggregate_res)
    
    # Devuelve algo para confirmar
    return {"success": True, "context": "Transaction Complete"}

def transactional_ops_with_errors(session=None):
    try:
        # 1️⃣ Intentamos insertar
        try:
            insert_res = dao.insert_one(item_doc, context="Insert Demo Item", session=session)
            ic("Insert Result:", insert_res)
        except DuplicateKeyError as e:
            ic(f"⚠️ Duplicate key detected: {e}")
            # Podríamos generar un nuevo ID o manejarlo según negocio
            return {"success": False, "message": "Duplicate Key", "context": "Insert Demo Item"}

        # 2️⃣ Actualizar
        if insert_res.get("success"):
            item_id = insert_res["data"]["_id"]
            update_res = dao.update_one(
                {"_id": ObjectId(item_id)},
                {"description": "Actualizado en transacción"},
                context="Update Demo Item",
                session=session
            )
            ic("Update Result:", update_res)

        # 3️⃣ Aggregate para contar items
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$group": {"_id": "$user_id", "total": {"$sum": 1}}}
        ]
        aggregate_res = dao.aggregate(pipeline, context="Aggregate Items By User", session=session)
        ic("Aggregate Result:", aggregate_res)

        return {"success": True, "context": "Transaction Complete"}

    except Exception as e:
        ic(f"❌ Error en transacción: {e}")
        return {"success": False, "message": str(e), "context": "Transaction Failed"}


# Ejecutar con manejo de transacción (si tu DAO soporta `with_transaction`)
try:
    transaction_result = dao.with_transaction(transactional_ops)
    transaction_result = dao.with_transaction(transactional_ops_with_errors)
    ic("Transaction Result:", transaction_result)
except Exception as e:
    ic(f"❌ Falló la transacción global: {e}")
# # Ejecutar todo dentro de una transacción
# transaction_result = dao.with_transaction(transactional_ops)
# ic("Transaction Result:", transaction_result)

