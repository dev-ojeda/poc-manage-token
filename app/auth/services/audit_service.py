
import datetime
from datetime import timezone
from bson import ObjectId

from app.dao import AuditLogDAO, SessionDAO
from app.model import AuditLogModel


class AuditService:
    def __init__(self):
        self.audit_log_dao = AuditLogDAO()
        self.session_dao = SessionDAO()

    def update_session_activity(
        self, 
        user_id: ObjectId, 
        ip_address: str | None, 
        user_agent: str | None, 
        reason: str | None
    ):
        """Actualiza actividad de la sesión y registra múltiples cambios relevantes en un solo evento"""
        session = self.session_dao.get_active_session_by_Id(user_id=user_id)
        if not session:
            raise ValueError("Sesión no encontrada")

        now_iso = datetime.datetime.now(tz=timezone.utc)

        # Normalizar valores
        current_browser = session.get("browser", "")
        new_browser = user_agent or ""
        current_reason = session.get("reason")

        # --- Detectar cambios ---
        changes = {}

        if current_browser != new_browser:
            changes["browser"] = {
                "old": current_browser,
                "new": new_browser
            }

        if reason and reason != current_reason:
            changes["reason"] = {
                "old": current_reason,
                "new": reason
            }

        # --- Si hubo cambios, auditar y actualizar ---
        if changes:
            audit_log = AuditLogModel(
                session_id=str(session["_id"]),
                user_id=str(session["user_id"]),
                event_type="session_update",   # unificado
                old_value=None,                # opcional: puedes dejar null
                new_value=None,                # opcional: puedes dejar null
                details=changes,               # 🔥 todos los cambios en un solo dict
                timestamp=now_iso,
                ip_address=ip_address,
                user_agent=new_browser,
            )
            self.audit_log_dao.insert_logs_audit(audit_log, context="session_update")

            return self.session_dao.update_session_for_audit(
                user_id=user_id,
                ip_address=ip_address,
                browser=new_browser,
                reason=reason or current_reason,  # conserva la razón previa si no vino nueva
            )

        return None  # explícito: no hubo cambios

    def get_logs_audit(self, **kwargs) -> dict:
        return self.audit_log_dao.get_logs_audit(**kwargs)
    def get_all_logs_audit(self) -> dict:
        return self.audit_log_dao.get_all_logs_audit()