from datetime import datetime, timezone
from typing import Optional, Dict
from bson import ObjectId

from app.core.base_service import BaseService
from app.dao.auditlog_dao import AuditLogDAO
from app.dao.session_dao import SessionDAO
from app.model.audit_session_model import AuditLogModel


class AuditService(BaseService):
    """Servicio para auditar cambios en sesiones y registrar logs."""

    def __init__(self, db=None, logger=None):
        super().__init__(db=db, logger=logger)
        self.audit_log_dao = AuditLogDAO(db=self.db)
        self.session_dao = SessionDAO(db=self.db)

    # -----------------------------
    # Actualización y auditoría de sesión
    # -----------------------------
    def update_session_activity(
        self,
        user_id: ObjectId,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Optional[Dict]:
        context = "update_session_activity"

        def fn():
            session = self.session_dao.get_active_session(user_id=user_id,device_id=device_id)
            if not session or not session.get("data"):
                raise ValueError("Sesión no encontrada")

            now_iso = datetime.now(tz=timezone.utc)
            data = session["data"]
            changes = {}

            # Detectar cambios
            if user_agent and user_agent != data.get("browser"):
                changes["browser"] = {"old": data.get("browser"), "new": user_agent}
            if reason and reason != data.get("reason"):
                changes["reason"] = {"old": data.get("reason"), "new": reason}

            if not changes:
                return None

            # Registrar auditoría
            audit_log = AuditLogModel(
                session_id=str(data["_id"]),
                user_id=str(data["user_id"]),
                event_type="session_update",
                old_value=None,
                new_value=None,
                details=changes,
                timestamp=now_iso,
                ip_address=ip_address,
                user_agent=user_agent or data.get("browser")
            )
            self.audit_log_dao.insert_logs_audit(audit_log, context=context)

            # Actualizar sesión
            return self.session_dao.update_session_for_audit(
                user_id=user_id,
                ip_address=ip_address,
                browser=user_agent or data.get("browser"),
                reason=reason or data.get("reason")
            )

        return self._safe_exec(fn, context=context)

    # -----------------------------
    # Consultas de logs
    # -----------------------------
    def get_logs_audit(self, **kwargs) -> Dict:
        return self._safe_exec(lambda: self.audit_log_dao.get_logs_audit(**kwargs), context="get_logs_audit")

    def get_all_logs_audit(self) -> Dict:
        return self._safe_exec(lambda: self.audit_log_dao.get_all_logs_audit(), context="get_all_logs_audit")
