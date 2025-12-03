# app/auth/services/container.py
from typing import Dict, Optional, Type
from app.logging_config import get_logger
from app.extensions import db_mongo
from app.auth.services.auth_service import AuthService
from app.auth.services.user_service import UserService
from app.auth.services.audit_service import AuditService
from app.auth.services.session_service import SessionService
from app.auth.services.blacklist_service import TokenBlacklistService
from app.auth.services.item_service import ItemService
from app.auth.services.performance_metrics_api_services import PerformanceMetricsApiService
from app.auth.services.metrics_service import MetricService
from app.auth.services.webauthn_service import WebAuthnCredentialService


class AuthContainer:
    """
    Contenedor único de servicios Auth.
    Inicializa servicios con DAO resilientes usando mongo_op.
    """

    _instances: Dict[str, object]

    def __init__(self, db=None, logger=None):
        self.db = db or db_mongo
        self.logger = logger or get_logger("AUTH_CONTAINER")
        self._instances = {}

    def _init_service(self, cls: Type, name: str, **kwargs) -> object:
        """Inicializa un servicio si no existe y lo guarda en _instances."""
        if name not in self._instances:
            self._instances[name] = cls(db=self.db, logger=self.logger, **kwargs)
            self.logger.debug(f"Servicio {name} inicializado")
        return self._instances[name]

    @property
    def auth_service(self) -> AuthService:
        return self._init_service(AuthService, "auth_service")

    @property
    def user_service(self) -> UserService:
        return self._init_service(UserService, "user_service")

    @property
    def audit_service(self) -> AuditService:
        return self._init_service(AuditService, "audit_service")

    @property
    def session_service(self) -> SessionService:
        return self._init_service(SessionService, "session_service")

    @property
    def blacklist_service(self) -> TokenBlacklistService:
        return self._init_service(TokenBlacklistService, "blacklist_service")

    @property
    def item_service(self) -> ItemService:
        return self._init_service(ItemService, "item_service")

    @property
    def performance_metrics_api_service(self) -> PerformanceMetricsApiService:
        return self._init_service(PerformanceMetricsApiService, "performance_metrics_api_service")

    @property
    def metric_service(self) -> MetricService:
        return self._init_service(MetricService, "metric_service")

    @property
    def webauthn_service(self) -> WebAuthnCredentialService:
        return self._init_service(WebAuthnCredentialService, "webauthn_service")

    @property
    def services(self) -> Dict[str, object]:
        return {name: getattr(self, name) for name in [
            "auth_service",
            "user_service",
            "audit_service",
            "session_service",
            "blacklist_service",
            "item_service",
            "performance_metrics_api_service",
            "metric_service",
            "webauthn_service"
        ]}

# -----------------------------
# Singleton global
# -----------------------------
_auth_container: Optional[AuthContainer] = None

def get_auth_services() -> AuthContainer:
    global _auth_container
    if _auth_container is None:
        _auth_container = AuthContainer()
    return _auth_container
