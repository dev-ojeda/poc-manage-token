from bson import ObjectId
from icecream import ic
from dao.session_dao import SessionDAO
from model.user_session import UserSession


class SessionService:
    def __init__(self):
        self.session_dao = SessionDAO()

    def register_session(self, user_session: UserSession) -> dict:
        return self.session_dao.insert_session(session=user_session)
    def revoke_session(self, user_id:ObjectId) -> dict:
        return self.session_dao.revoked_session(user_id=user_id, reason="revocación")
    def update_session(self, user_id:ObjectId) -> dict:
        return self.session_dao.update_session(user_id=user_id, reason="terminada")
    def get_active_session(self, user_id:ObjectId, device_id: str) -> dict:
        return self.session_dao.get_active_session(user_id=user_id,device_id=device_id)
    @staticmethod
    def get_non_admin_active_sessions(filtro_status: str = None):
        
        sd = SessionDAO()
        sessions = sd.get_active_sessions_with_user_data(filtro_status=filtro_status)
        
        result = []
        for s in sessions:
            result.append({
                "session_id": str(s["_id"]),
                "user_id": str(s["user_id"]),
                "ip_address": s["ip_address"],
                "browser": s["browser"],
                "os": s["os"],
                "device_id": s["device_id"],
                "login_at": s["login_at"].isoformat(),
                "last_refresh_at": s["last_refresh_at"].isoformat(),
                "refresh_token": s["refresh_token"],
                "is_revoked": s["is_revoked"],
                "reason": s["reason"],
                "status": s["status"],
                "username": s["user_data"]["username"],
                "rol": s["user_data"]["rol"]
            })
        ic(f"[SESSION DAO]: {result}")
        return result
