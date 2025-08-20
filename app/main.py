#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

import eventlet
import eventlet.wsgi
from icecream import ic

from app import create_app
from app.config import Config

app = create_app()
ic.configureOutput(prefix="debug-",includeContext=True)
def main() -> None:
    """
    Punto de entrada principal de la app.
    """
    ic("🚀 Servidor iniciado en:")
    ic(f"🌐 http://{Config.HOST}:{Config.PORT}")
    ic(f"🔒 https://{Config.HOST}:{Config.PORT} (si SSL está activo)")

    use_ssl = os.getenv("FLASK_USE_SSL", "false").lower() == "true"

    listener = eventlet.listen((Config.HOST, Config.PORT))

    if use_ssl:
        ssl_args = {
            "certfile": Config.PATH_CRT,
            "keyfile": Config.PATH_KEY,
            "server_side": True
        }
        listener = eventlet.wrap_ssl(listener, **ssl_args)
        ic("✅ SSL habilitado")

    # Lanza el servidor WSGI
    eventlet.wsgi.server(listener, app, log_output=True)

if __name__ == "__main__":
    main()
