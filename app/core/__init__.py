# app/core/__init__.py
# Este paquete centraliza la lógica base de la aplicación (DAO y Services).

from .base_dao import BaseDAO
from .base_service import BaseService

__all__ = ["BaseDAO", "BaseService"]
