from flask import Blueprint
import importlib
import pkgutil
import logging

logger = logging.getLogger("FRONTEND_INIT")

frontend_bp = Blueprint(
    "frontend",
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder="templates"
)

# Autoregistro de sub-blueprints detectando submódulos dinámicamente
package = importlib.import_module("app.frontend")
for _, mod_name, is_pkg in pkgutil.iter_modules(package.__path__):
    if not is_pkg:
        continue
    try:
        submod = importlib.import_module(f"frontend.{mod_name}")
        if hasattr(submod, "bp") and isinstance(submod.bp, Blueprint):
            frontend_bp.register_blueprint(submod.bp)
            logger.info(f"🧩 Sub-blueprint registrado: frontend.{mod_name}")
        else:
            logger.warning(f"⚠️ No se encontró 'bp' en frontend.{mod_name}")
    except Exception as e:
        logger.error(f"⚠️ Error registrando frontend.{mod_name}: {e}")
