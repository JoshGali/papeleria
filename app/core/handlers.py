"""Manejadores globales de excepciones (Requerimiento 9).

Centralizan la traduccion de cualquier fallo a la respuesta JSON unica de la
API y garantizan el registro en bitacora exigido por los Req 7.1-7.11 y 9.8.
"""

import logging
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    DEFAULT_STATUS_MESSAGES,
    STATUS_TO_ERROR_TYPE,
    ErrorType,
    InventoryError,
    build_error_payload,
)
from app.core.logging import log_error

#: Tipos de error de Pydantic que indican un cuerpo JSON mal formado (Req 7.1).
_JSON_ERROR_TYPES = {"json_invalid", "json_type"}


def _location(loc: Any) -> str:
    """Convierte la tupla ``loc`` de Pydantic en un nombre de campo legible."""
    parts = [str(item) for item in loc if item not in ("body", "query", "path")]
    return ".".join(parts) if parts else "body"


#: Prefijo que Pydantic antepone a los mensajes de un validador propio.
_PYDANTIC_PREFIX = "Value error, "


def _clean_message(message: str) -> str:
    """Quita el prefijo tecnico de Pydantic para exponer el texto del dominio."""
    text = str(message)
    if text.startswith(_PYDANTIC_PREFIX):
        return text[len(_PYDANTIC_PREFIX) :]
    return text


def _as_error_details(raw_errors: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Normaliza los errores de Pydantic al arreglo del Req 9.4."""
    details: List[Dict[str, str]] = []
    for error in raw_errors:
        details.append(
            {
                "field": _location(error.get("loc", ())),
                "message": _clean_message(error.get("msg", "Valor invalido")),
                "type": str(error.get("type", "value_error")),
            }
        )
    return details


def _summary_message(details: List[Dict[str, str]]) -> str:
    """Resume los errores respetando el rango de 10-200 caracteres (Req 9.1)."""
    if not details:
        return DEFAULT_STATUS_MESSAGES[400]
    if len(details) == 1:
        only = details[0]
        return f"Error de validacion en '{only['field']}': {only['message']}"
    fields = ", ".join(sorted({item["field"] for item in details}))
    return (
        f"Se encontraron {len(details)} errores de validacion "
        f"en los campos: {fields}"
    )


def _json_response(payload: Dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=payload["status_code"], content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra en la aplicacion todos los manejadores de error."""

    @app.exception_handler(InventoryError)
    async def handle_inventory_error(
        request: Request, exc: InventoryError
    ) -> JSONResponse:
        """Errores de dominio: 400, 404, 409, 503 y 507."""
        payload = exc.to_payload()
        log_error(
            status_code=exc.status_code,
            error_type=exc.error_type,
            message=exc.message,
            method=request.method,
            path=request.url.path,
            details=exc.errors or None,
        )
        return _json_response(payload)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Req 7: toda entrada invalida se rechaza con 400, nunca con 422."""
        details = _as_error_details(exc.errors())
        is_json_error = any(item["type"] in _JSON_ERROR_TYPES for item in details)
        if is_json_error:
            # Req 7.1: el cuerpo no es JSON valido.
            message = "El cuerpo de la peticion no es un JSON valido (JSON parse failure)"
            details = [
                {
                    "field": "body",
                    "message": "JSON parse failure",
                    "type": "json_invalid",
                }
            ]
        else:
            message = _summary_message(details)

        payload = build_error_payload(
            error_type=ErrorType.VALIDATION,
            message=message,
            status_code=400,
            errors=details,
        )
        log_error(
            status_code=400,
            error_type=ErrorType.VALIDATION,
            message=payload["message"],
            method=request.method,
            path=request.url.path,
            details=details,
        )
        return _json_response(payload)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Errores generados por el framework: 404 de ruta, 405, etc."""
        status_code = exc.status_code
        error_type = STATUS_TO_ERROR_TYPE.get(status_code, ErrorType.INTERNAL)
        detail = exc.detail if isinstance(exc.detail, str) else None
        message = DEFAULT_STATUS_MESSAGES.get(status_code) or (
            detail or "Error procesando la solicitud recibida"
        )
        payload = build_error_payload(
            error_type=error_type, message=message, status_code=status_code
        )
        log_error(
            status_code=status_code,
            error_type=error_type,
            message=payload["message"],
            method=request.method,
            path=request.url.path,
            details=detail,
        )
        return _json_response(payload)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Req 9.5: cualquier excepcion no controlada termina en 500."""
        payload = build_error_payload(
            error_type=ErrorType.INTERNAL,
            message="An internal error occurred",
            status_code=500,
        )
        log_error(
            status_code=500,
            error_type=ErrorType.INTERNAL,
            message=f"{type(exc).__name__}: {exc}",
            method=request.method,
            path=request.url.path,
            level=logging.ERROR,
        )
        return _json_response(payload)
