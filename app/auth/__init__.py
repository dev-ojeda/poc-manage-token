__all__ = ["get_auth_services", "AuthContainer"]

def get_auth_services():
    from .container import get_auth_services as _get_auth_services
    return _get_auth_services()

def AuthContainer():
    from .container import AuthContainer as _AuthContainer
    return _AuthContainer