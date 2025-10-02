import datetime
from typing import Optional, List, Dict
from bson import ObjectId

from app.dao.session_dao import SessionDAO
from app.model.user_session_model import UserSessionModel


class SessionService:
    """
    Servicio para gestionar sesiones activas de usuarios.
    """
    def __init__(self):
        self.session_dao = SessionDAO()

    # --------------------------
    # Registro y actualización de sesiones
    # --------------------------
    def register_session(self, user_session: UserSessionModel) -> dict:
        return self.session_dao.insert_session(session=user_session)

    def revoke_session(self, user_id: ObjectId, reason: str = "revoked") -> dict:
        return self.session_dao.revoked_session(user_id=user_id, reason=reason)

    def update_session(self, user_id: ObjectId, token: str, reason: str) -> dict:
        return self.session_dao.update_session(user_id=user_id, token=token, reason=reason)

    def update_session_for_audit(
        self, user_id: ObjectId, ip_address: str, browser: str, reason: str
    ) -> dict:
        return self.session_dao.update_session_for_audit(
            user_id=user_id, ip_address=ip_address, browser=browser, reason=reason
        )

    # --------------------------
    # Consultas de sesiones
    # --------------------------
    def get_active_session(self, user_id: ObjectId, device_id: str) -> Optional[dict]:
        return self.session_dao.get_active_session(user_id=user_id, device_id=device_id)

    def get_active_session_by_id(self, user_id: ObjectId) -> Optional[dict]:
        return self.session_dao.get_active_session(user_id=user_id)

    def device_id_exists(self, device_id: str) -> bool:
        return bool(self.session_dao.device_id_exists(device_id=device_id))

    def has_active_session(self, user_id: ObjectId) -> bool:
        return self.session_dao.has_active_session(user_id=user_id)

    # --------------------------
    # Consultas globales
    # --------------------------
    def get_non_admin_active_sessions(self, filtro_status: Optional[str] = None) -> List[Dict]:
        """
        Devuelve todas las sesiones activas de usuarios no administradores,
        normalizando los campos de fecha a ISO y mapeando información relevante.
        """
        sessions = self.session_dao.get_active_sessions_with_user_data(filtro_status=filtro_status)
        result: List[Dict] = []

        for s in sessions.get("data", []):
            user_data = s.get("user_data", {})
            result.append({
                "session_id": str(s.get("_id")),
                "user_id": str(s.get("user_id")),
                "ip_address": s.get("ip_address"),
                "browser": s.get("browser"),
                "os": s.get("os"),
                "device_id": s.get("device_id"),
                "login_at": self._to_iso(s.get("login_at")),
                "last_refresh_at": self._to_iso(s.get("last_refresh_at")),
                "refresh_token": s.get("refresh_token"),
                "is_revoked": s.get("is_revoked", False),
                "reason": s.get("reason"),
                "status": s.get("status"),
                "username": user_data.get("username"),
                "rol": user_data.get("rol")
            })

        return result

    # --------------------------
    # Utils
    # --------------------------
    @staticmethod
    def _to_iso(dt: Optional[datetime.datetime]) -> Optional[str]:
        if dt and isinstance(dt, datetime.datetime):
            return dt.isoformat()
        return None
