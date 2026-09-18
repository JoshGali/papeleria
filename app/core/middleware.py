"""Middlewares transversales de la API.

Cubren dos criterios que no pueden resolverse dentro de un endpoint:
Req 9.5 (excepcion no controlada -> 500) y Req 9.6 (peticion que supera los
30 segundos -> 504).
"""

import asyncio
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import REQUEST_TIMEOUT_SECONDS
from app.core.errors import ErrorType, build_error_payload
from app.core.logging import get_logger, log_error


class TimeoutAndErrorMiddleware(BaseHTTPMiddleware):
    """Aplica el limite de tiempo y actua como red de seguridad de errores.

    Se ubica por fuera del enrutador, de modo que atrapa tambien los fallos
    que ocurren antes de resolver un endpoint.
    """

    def __init__(self, app, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS) -> None:
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        started = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                call_next(request), timeout=self.timeout_seconds
            )
        except (asyncio.TimeoutError, TimeoutError):
            # Req 9.6: la peticion no termino dentro del tiempo permitido.
            payload = build_error_payload(
                error_type=ErrorType.TIMEOUT,
                message=(
                    "La solicitud excedio el tiempo maximo de "
                    f"{self.timeout_seconds:g} segundos y fue cancelada"
                ),
                status_code=504,
            )
            log_error(
                status_code=504,
                error_type=ErrorType.TIMEOUT,
                message=payload["message"],
                method=request.method,
                path=request.url.path,
            )
            return JSONResponse(status_code=504, content=payload)
        except Exception as exc:  # noqa: BLE001 - red de seguridad deliberada
            # Req 9.5: ninguna excepcion debe escapar sin respuesta JSON.
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
            return JSONResponse(status_code=500, content=payload)

        elapsed_ms = (time.perf_counter() - started) * 1000
        get_logger().info(
            "method=%s | path=%s | status=%s | elapsed_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
