class AuthException(Exception):
    def __init__(self, message, code, status):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
