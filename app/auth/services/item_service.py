from typing import List, Dict, Any, Optional
from app.core.base_service import BaseService
from app.dao.item_dao import ItemDAO
from app.model.item_model import ItemModel


class ItemService(BaseService):
    """
    Servicio para manejar operaciones sobre Items.
    Hereda BaseService para logging y manejo seguro de errores.
    """

    dao: Optional[ItemDAO] = None

    def __init__(self, db=None, logger=None, dao: Optional[ItemDAO] = None):
        super().__init__(db=db, dao=dao, logger=logger)
        self.dao = dao or ItemDAO()

    # --------------------------
    # Crear Item
    # --------------------------
    def insert_item(self, item_model: ItemModel) -> Dict[str, Any]:
        """
        Inserta un nuevo item para un usuario.
        """
        return self._safe_exec(self.dao.create, item_model=item_model, context="insert_item")

    # --------------------------
    # Validar payload
    # --------------------------
    def validate_item_payload(self, data: dict) -> List[str]:
        """
        Valida que los campos obligatorios estén presentes.
        """
        required_fields = ["user_id", "name"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            self._log_debug(f"Payload inválido, campos faltantes: {missing}")
        return missing

    # --------------------------
    # Obtener items por usuario
    # --------------------------
    def get_all_by_user(self, user_id: str) -> Dict[str, Any]:
        """
        Devuelve todos los items asociados a un usuario.
        """
        return self._safe_exec(self.dao.get_all_by_user, user_id=user_id, context="get_all_by_user")
