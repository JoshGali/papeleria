"""Punto de entrada de la API del Gestor de Inventario de la papeleria."""

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI

from app.api.routes_products import router as products_router
from app.api.routes_stock import router as stock_router
from app.core.config import API_TITLE, API_VERSION, STORE_MAX_PRODUCTS
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import TimeoutAndErrorMiddleware
from app.store.memory_store import store

DESCRIPTION = """
API REST para administrar el inventario de la papeleria.

Permite crear, consultar, actualizar y eliminar productos, registrar entradas
y salidas de stock y consultar disponibilidad. La persistencia es en memoria
(Requerimiento 10) y se pierde al detener el proceso.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa y libera el In_Memory_Store (Req 10.2, 10.4 y 10.5)."""
    configure_logging()
    store.initialize()
    get_logger().info(
        "Inventory_System iniciado | capacidad=%s productos", STORE_MAX_PRODUCTS
    )
    try:
        yield
    finally:
        store.shutdown()
        get_logger().info("Inventory_System detenido | almacen en memoria liberado")


def create_app() -> FastAPI:
    """Construye la aplicacion FastAPI con middlewares y routers."""
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=DESCRIPTION,
        lifespan=lifespan,
    )

    # Req 9.5 y 9.6: limite de tiempo y red de seguridad ante fallos.
    app.add_middleware(TimeoutAndErrorMiddleware)
    # Req 9: formato unico de error para todo el sistema.
    register_exception_handlers(app)

    app.include_router(products_router)
    app.include_router(stock_router)

    @app.get("/health", tags=["Sistema"], summary="Estado del sistema")
    def health() -> Dict[str, Any]:
        """Reporta el estado del almacen sin aplicar el filtro del Req 2."""
        initialized = store.is_initialized
        return {
            "status": "ok" if initialized else "unavailable",
            "store_initialized": initialized,
            "products": store.count() if initialized else 0,
            "capacity": store.capacity,
        }

    return app


app = create_app()
