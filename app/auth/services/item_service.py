from typing import List

from app.dao.item_dao import ItemDAO
from app.model.item_model import ItemModel


class ItemService:
    """
    Servicio para manejar operaciones sobre Items.
    """

    def __init__(self):
        self.item_dao = ItemDAO()

    # --------------------------
    # Crear Item
    # --------------------------
    def insert_item(self, item_model: ItemModel) -> dict:
        """
        Inserta un nuevo item para un usuario.
        """
        return self.item_dao.create(item_model=item_model)

    # --------------------------
    # Validar payload
    # --------------------------
    def validate_item_payload(self, data: dict) -> List[str]:
        """
        Valida que los campos obligatorios estén presentes.
        """
        required_fields = ["user_id", "name"]
        return [field for field in required_fields if not data.get(field)]

    # --------------------------
    # Obtener items por usuario
    # --------------------------
    def get_all_by_user(self, user_id: str) -> dict:
        """
        Devuelve todos los items asociados a un usuario.
        """
        return self.item_dao.get_all_by_user(user_id=user_id)
