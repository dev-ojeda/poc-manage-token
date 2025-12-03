from datetime import datetime
from typing import Optional
from bson import ObjectId
from app.dao.session_dao import SessionDAO
from app.model.user_session_model import UserSessionModel
from app.core.base_service import BaseService


class SessionService(BaseService[SessionDAO]):
    """
    Servicio para gestionar sesiones activas de usuarios.
    Refactorizado sobre BaseService para logging y safe_exec.
    """

    dao: SessionDAO = SessionDAO()  # ahora BaseService detecta un DAO

    def __init__(self, db=None, session_dao: Optional[SessionDAO] = None, logger=None):
        super().__init__(db=db, dao=self.dao, logger=logger)
        self.dao = session_dao or SessionDAO(db=self.db, logger=self.logger)

    # --------------------------
    # Registro y actualización de sesiones
    # --------------------------
    def register_session(self, user_session: UserSessionModel) -> dict:
        return self._safe_exec(lambda: self.dao.insert_session(session=user_session), context="register_session")

    def revoke_session(self, user_id: ObjectId, reason: str = "revoked") -> dict:
        return self._safe_exec(lambda: self.dao.revoke_session(user_id=user_id, reason=reason), context="revoke_session")

    def update_session(self, user_id: ObjectId, token: str, reason: str) -> dict:
        return self._safe_exec(lambda: self.dao.update_session(user_id=user_id, token=token, reason=reason), context="update_session")

    def update_session_for_audit(self, user_id: ObjectId, ip_address: str, browser: str, reason: str) -> dict:
        return self._safe_exec(
            lambda: self.dao.update_session_for_audit(
            user_id=user_id,
            ip_address=ip_address,
            browser=browser,
            reason=reason),
            context="update_session_for_audit"
        )

    # --------------------------
    # Consultas de sesiones
    # --------------------------
    def get_active_session_by_id(self, user_id: ObjectId, device_id: str) -> Optional[dict]:
        return self._safe_exec(lambda: self.dao.get_active_session(user_id=user_id, device_id=device_id), context="get_active_session_by_id")

    def device_id_exists(self, device_id: str) -> bool:
        return bool(self._safe_exec(lambda: self.dao.device_id_exists(device_id=device_id), context="device_id_exists"))

    def has_active_session(self, user_id: ObjectId) -> bool:
        return bool(self._safe_exec(lambda: self.dao.has_active_session(user_id=user_id), context="has_active_session"))

    # --------------------------
    # Consultas globales
    # --------------------------
    def get_non_admin_active_sessions(self, filtro_status: Optional[str] = None) -> dict:
        return self._safe_exec(
            lambda: self.dao.get_active_sessions_with_user_data(filtro_status=filtro_status),
            context="get_non_admin_active_sessions"
        )

    # --------------------------
    # Utils
    # --------------------------
    @staticmethod
    def _to_iso(dt: Optional[datetime]) -> Optional[str]:
        if dt and isinstance(dt, datetime):
            return dt.isoformat()
        return None
