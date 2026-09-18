"""Excepciones de dominio y formato unico de respuesta de error.

Req 9: toda respuesta de error viaja en JSON con los campos ``error_type``,
``message`` (entre 10 y 200 caracteres) y ``status_code``. Cuando una peticion
acumula varios errores de validacion se agrega el arreglo ``errors``
(Req 9.4).
"""

from typing import Any, Dict, List, Optional

from app.core.config import ERROR_MESSAGE_MAX_LENGTH, ERROR_MESSAGE_MIN_LENGTH


class ErrorType:
    """Valores admitidos del campo ``error_type`` (Req 9.1-9.7)."""

    VALIDATION = "validation_error"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INTERNAL = "internal_error"
    TIMEOUT = "timeout"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    SERVICE_UNAVAILABLE = "service_unavailable"
    STORAGE_CAPACITY_EXCEEDED = "storage_capacity_exceeded"


def normalize_message(message: str) -> str:
    """Ajusta un mensaje al rango exigido por Req 9.1-9.3 (10-200 caracteres).

    Los mensajes cortos se completan con un sufijo descriptivo y los largos se
    truncan conservando un elipsis, de modo que el contrato nunca se rompa.
    """
    text = " ".join((message or "").split()) or "Error procesando la solicitud"
    if len(text) > ERROR_MESSAGE_MAX_LENGTH:
        return text[: ERROR_MESSAGE_MAX_LENGTH - 3].rstrip() + "..."
    if len(text) < ERROR_MESSAGE_MIN_LENGTH:
        padded = f"{text} (error de la solicitud)"
        return padded[:ERROR_MESSAGE_MAX_LENGTH]
    return text


def build_error_payload(
    *,
    error_type: str,
    message: str,
    status_code: int,
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construye el cuerpo JSON de error comun a toda la API."""
    payload: Dict[str, Any] = {
        "error_type": error_type,
        "message": normalize_message(message),
        "status_code": status_code,
    }
    if errors:
        payload["errors"] = errors
    return payload


class InventoryError(Exception):
    """Base de los errores de negocio del Inventory_System."""

    error_type: str = ErrorType.INTERNAL
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        errors: Optional[List[Dict[str, Any]]] = None,
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
    ) -> None:
        self.message = normalize_message(message)
        self.errors = errors or []
        if status_code is not None:
            self.status_code = status_code
        if error_type is not None:
            self.error_type = error_type
        super().__init__(self.message)

    def to_payload(self) -> Dict[str, Any]:
        return build_error_payload(
            error_type=self.error_type,
            message=self.message,
            status_code=self.status_code,
            errors=self.errors,
        )


class ValidationError(InventoryError):
    """Datos de entrada invalidos (Req 7, Req 9.1) -> 400."""

    error_type = ErrorType.VALIDATION
    status_code = 400


class NotFoundError(InventoryError):
    """Recurso inexistente o filtrado (Req 2.2, 2.3, Req 9.2) -> 404."""

    error_type = ErrorType.NOT_FOUND
    status_code = 404


class ConflictError(InventoryError):
    """Recurso duplicado (Req 9.3) -> 409."""

    error_type = ErrorType.CONFLICT
    status_code = 409


class StoreNotReadyError(InventoryError):
    """El In_Memory_Store aun no se inicializa (Req 2.6) -> 503."""

    error_type = ErrorType.SERVICE_UNAVAILABLE
    status_code = 503


class StorageCapacityError(InventoryError):
    """El In_Memory_Store alcanzo su capacidad (Req 10.3) -> 507."""

    error_type = ErrorType.STORAGE_CAPACITY_EXCEEDED
    status_code = 507


#: Mapeo de codigos HTTP a ``error_type`` para errores que no nacen del dominio
#: (por ejemplo los que genera Starlette antes de llegar a un endpoint).
STATUS_TO_ERROR_TYPE: Dict[int, str] = {
    400: ErrorType.VALIDATION,
    404: ErrorType.NOT_FOUND,
    405: ErrorType.METHOD_NOT_ALLOWED,
    409: ErrorType.CONFLICT,
    500: ErrorType.INTERNAL,
    503: ErrorType.SERVICE_UNAVAILABLE,
    504: ErrorType.TIMEOUT,
    507: ErrorType.STORAGE_CAPACITY_EXCEEDED,
}

#: Mensajes por defecto, ya dentro del rango de 10-200 caracteres.
DEFAULT_STATUS_MESSAGES: Dict[int, str] = {
    400: "La solicitud contiene datos invalidos y fue rechazada",
    404: "El recurso solicitado no existe en el inventario",
    405: "El metodo HTTP no esta permitido para esta ruta",
    409: "El recurso ya existe y genera un conflicto de datos",
    500: "An internal error occurred",
    503: "El almacenamiento en memoria no esta listo para atender",
    504: "La solicitud excedio el tiempo maximo de 30 segundos",
    507: "Se excedio la capacidad de almacenamiento del inventario",
}
