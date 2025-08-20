from app.dao.blacklist_dao import TokenBlacklistDao


class TokenBlacklistService():
    def __init__(self):
        self.blacklist_dao = TokenBlacklistDao()

    def revoke_token_blacklist(self, token: str, device_id: None, username: None, reason: None) -> dict:
        return self.blacklist_dao.revoke_token_blacklist(token=token,device_id=device_id,username=username,reason=reason)



