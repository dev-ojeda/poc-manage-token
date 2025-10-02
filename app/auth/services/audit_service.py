import datetime
from datetime import timezone
from bson import ObjectId
from typing import Optional, Dict, Any

from app.dao.audit_dao import AuditLogDAO
from app.dao.session_dao import SessionDAO
from app.model.audit_session_model import AuditLogModel


class AuditService:
    """
    Servicio para auditar cambios en sesiones y registrar logs de auditoría.
    """

    def __init__(self):
        self.audit_log_dao = AuditLogDAO()
        self.session_dao = SessionDAO()

    # -------------------------------
    # Actualización y auditoría de sesión
    # -------------------------------
    def update_session_activity(
        self,
        user_id: ObjectId,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza actividad de la sesión y registra cambios relevantes en un solo evento de auditoría.

        :param user_id: ID del usuario
        :param ip_address: nueva IP (opcional)
        :param user_agent: nuevo navegador/dispositivo (opcional)
        :param reason: motivo del cambio (opcional)
        :return: resultado de la actualización de sesión o None si no hubo cambios
        """
        session = self.session_dao.get_active_session(user_id=user_id)
        if not session:
            raise ValueError("Sesión no encontrada")

        now_iso = datetime.datetime.now(tz=timezone.utc)
        current_browser = session["data"]["browser"]
        current_reason =  session["data"]["reason"]

        # --- Detectar cambios ---
        changes = {}
        if user_agent and user_agent != current_browser:
            changes["browser"] = {"old": current_browser, "new": user_agent}
        if reason and reason != current_reason:
            changes["reason"] = {"old": current_reason, "new": reason}

        # --- Si hubo cambios, auditar y actualizar ---
        if changes:
            audit_log = AuditLogModel(
                session_id=str(session["data"]["_id"]),
                user_id=str(session["data"]["user_id"]),
                event_type="session_update",
                old_value=None,
                new_value=None,
                details=changes,
                timestamp=now_iso,
                ip_address=ip_address,
                user_agent=user_agent or current_browser
            )
            self.audit_log_dao.insert_logs_audit(audit_log, context="session_update")

            return self.session_dao.update_session_for_audit(
                user_id=user_id,
                ip_address=ip_address,
                browser=user_agent or current_browser,
                reason=reason or current_reason
            )

        return None  # No hubo cambios

    # -------------------------------
    # Consultas de logs
    # -------------------------------
    def get_logs_audit(self, **kwargs) -> dict:
        """
        Obtiene logs de auditoría con filtros opcionales.
        """
        return self.audit_log_dao.get_logs_audit(**kwargs)

    def get_all_logs_audit(self) -> dict:
        """
        Devuelve todos los logs de auditoría.
        """
        return self.audit_log_dao.get_all_logs_audit()
