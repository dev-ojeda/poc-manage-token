from app.logging_config import setup_logging

logger = setup_logging().getChild(__name__)

logger.debug("Mensaje de debug (solo visible si LOG_LEVEL=DEBUG)")
logger.info("Proceso iniciado correctamente ✅")
logger.warning("Atención: uso intensivo de CPU ⚙️")
logger.error("Error de conexión a base de datos 💥")
logger.critical("¡Falla crítica del sistema! 🚨")
