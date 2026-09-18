"""Configuracion de logging del Gestor de Inventario.

Req 7.1-7.11: toda peticion rechazada se registra con timestamp y detalle.
Req 9.8: todo error se registra con timestamp, ruta, metodo y detalle.
"""

import logging
import sys
from typing import Any, Mapping, Optional

LOGGER_NAME = "inventory"

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Instala un handler de consola idempotente para el logger del sistema."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def log_error(
    *,
    status_code: int,
    error_type: str,
    message: str,
    method: str = "-",
    path: str = "-",
    details: Optional[Any] = None,
    level: int = logging.WARNING,
) -> None:
    """Registra un error/rechazo con el contexto exigido por Req 9.8.

    El timestamp lo aporta el formateador del handler (campo ``asctime``).
    """
    logger = get_logger()
    parts = [
        f"status={status_code}",
        f"error_type={error_type}",
        f"method={method}",
        f"path={path}",
        f"message={message!r}",
    ]
    if details:
        parts.append(f"details={_compact(details)}")
    logger.log(level, " | ".join(parts))


def _compact(details: Any) -> str:
    """Serializa los detalles de error de forma breve y estable."""
    if isinstance(details, Mapping):
        return "{" + ", ".join(f"{k}={v}" for k, v in details.items()) + "}"
    if isinstance(details, (list, tuple)):
        return "[" + "; ".join(_compact(item) for item in details) + "]"
    return str(details)
