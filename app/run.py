#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from icecream import ic

from app import create_app
from config import Config

app = create_app()

def main() -> None:
    """
    Punto de entrada principal de la app.
    """
    ic("🚀 Servidor iniciado en:")
    ic(f"🌐 http://localhost:{Config.PORT}")
    ic(f"🌐 https://localhost:{Config.PORT}")
    ic(f"🔒 https://localhost:{Config.PORT} (SSL activo)")
    ic(f"🔒 https://127.0.0.1:{Config.PORT} (SSL activo)")

    # Detectar entorno para toggle de SSL
    use_ssl = os.getenv("FLASK_USE_SSL", "true").lower() == "true"

    if use_ssl:
        app.run(ssl_context=(Config.PATH_CRT_APP, Config.PATH_KEY_APP),host=Config.HOST,port=Config.PORT,debug=False)
    else:
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG
        )


if __name__ == "__main__":
    main()
    