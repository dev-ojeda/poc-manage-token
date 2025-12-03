# app/dao/__init__.py
"""
Módulo DAO (Data Access Objects)
Centraliza todas las clases de acceso a datos de MongoDB.
Carga dinámica para evitar imports circulares.
"""

import logging
import re
from importlib import import_module

logger = logging.getLogger("app.dao")

__all__ = [
    "AuditLogDAO",
    "AuthDAO",
    "TokenBlacklistDAO",
    "SessionDAO",
    "UserDAO",
    "ItemDAO",
    "PerformanceMetricsApiDAO",
    "MetricsDAO",
    "WebAuthnDAO"
]

for dao_name in __all__:
    # Convierte la clase a snake_case + "_dao"
    module_name = re.sub(r"(DAO|Dao)$", "", dao_name).lower() + "_dao"
    try:
        module = import_module(f"app.dao.{module_name}")
        globals()[dao_name] = getattr(module, dao_name)
    except (ModuleNotFoundError, AttributeError) as e:
        logger.error(f"[DAO INIT] No se pudo importar {dao_name} desde {module_name}: {e}")
        # En desarrollo puedes comentar la siguiente línea si quieres que siga cargando otros DAOs
        raise ImportError(f"No se pudo importar {dao_name} desde {module_name}: {e}") from e
