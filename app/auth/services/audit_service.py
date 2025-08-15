from datetime import datetime, timezone

from bson import ObjectId

from app.dao.audit_dao import AuditLogDAO
from app.dao.session_dao import SessionDAO
from app.model.audit_session import AuditLog


class AuditService:
    def __init__(self):
        self.audit_log_dao = AuditLogDAO()
        self.session_dao = SessionDAO()

    def update_session_activity(self, user_id: ObjectId, ip_address: str | None, user_agent: str | None):
        """Actualiza actividad de la sesión y registra cambios relevantes"""
        session = self.session_dao.get_active_session_by_Id(user_id=user_id)
        if not session:
            raise ValueError("Sesión no encontrada")

        now_iso = self.get_datetime_now()
        reason = ""
        cambios = False

        # Detectar cambio de navegador/User-Agent
        if session.get("browser") != user_agent:
            audit_log = AuditLog(
                session_id=str(session["_id"]),
                user_id=str(session["user_id"]),
                event_type="user_agent_change",
                old_value=session.get("browser", ""),
                new_value=user_agent,
                timestamp=now_iso,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.audit_log_dao.insert_logs_audit(audit_log=audit_log, context="user_agent_change")
            reason = "user_agent_change"
            cambios = True

        # Registrar auditoría por razón previa
        if session.get("reason"):
            audit_log = AuditLog(
                session_id=str(session["_id"]),
                user_id=str(session["user_id"]),
                event_type=session["reason"],
                old_value=session.get("browser", ""),
                new_value=user_agent,
                timestamp=now_iso,
                ip_address=session.get("ip_address"),
                user_agent=user_agent
            )
            self.audit_log_dao.insert_logs_audit(audit_log=audit_log, context="reason_auditoria")
            cambios = True
            if not reason:  # si no había cambio de user-agent
                reason = session["reason"]

        # Actualizar sesión solo si hubo cambios
        if cambios:
            return self.session_dao.update_session_for_audit(
                user_id=user_id,
                ip_address=ip_address,
                browser=user_agent,
                reason=reason
            )

    def get_logs_audit(self, **kwargs) -> dict:
        return self.audit_log_dao.get_logs_audit(**kwargs)

    def get_datetime_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def update_datetime_format_iso(self, fecha: datetime) -> str:
        return fecha.astimezone(timezone.utc).isoformat()