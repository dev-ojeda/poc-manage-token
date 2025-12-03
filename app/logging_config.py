# app/logging_config.py
import logging
import logging.handlers
import sys
import os
import json
import traceback
import queue
import atexit

RESET = "\033[0m"
COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[41m",
}

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_listener = None
_logger_initialized = False


class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{RESET}"
        return super().format(record)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(log_record, ensure_ascii=False)


def setup_logging():
    """Inicializa logging asíncrono global con rotación de archivos."""
    global _listener, _logger_initialized

    if _logger_initialized:
        return logging.getLogger()  # Evita reinicialización

    root = logging.getLogger()
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    use_json = os.getenv("LOG_JSON", "false").lower() == "true"
    log_dir = os.getenv("LOG_DIR", "./logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    formatter = JsonFormatter() if use_json else ColorFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when=os.getenv("LOG_ROTATE_WHEN", "midnight"),
        interval=int(os.getenv("LOG_ROTATE_INTERVAL", 1)),
        backupCount=int(os.getenv("LOG_ROTATE_BACKUP", 7)),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)

    root.setLevel(level)
    root.addHandler(queue_handler)

    _listener = logging.handlers.QueueListener(log_queue, stream_handler, file_handler)
    _listener.start()

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("engineio").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)

    _logger_initialized = True
    root.info(f"Logging asíncrono con rotación iniciado (level={level_name}, json={use_json})")
    return root


def get_logger(name: str = None) -> logging.Logger:
    """Devuelve un logger hijo, inicializando logging global solo la primera vez."""
    if not _logger_initialized:
        setup_logging()
    return logging.getLogger(name)


@atexit.register
def shutdown_logging():
    global _listener
    try:
        if _listener:
            logging.getLogger(__name__).info("🧹 Deteniendo QueueListener...")
            _listener.stop()
            logging.getLogger(__name__).info("QueueListener detenido correctamente.")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error al detener logging: {e}")
