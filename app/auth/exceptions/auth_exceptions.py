class AuthException(Exception):
    def __init__(self, message, code, status, tipo):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.tipo = tipo

    def to_dict(self):
        return {
            "message": self.message,
            "code": self.code,
            "status": self.status,
            "tipo": self.tipo
        }

    @staticmethod
    def from_dict(data: dict) -> "AuthException":
        return AuthException(
            message=data["message"],
            code=data["code"],
            status=data["status"],
            tipo=data["tipo"]
        )