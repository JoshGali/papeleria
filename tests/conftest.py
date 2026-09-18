"""Fixtures compartidas por la suite de pruebas."""

import logging
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.inventory_service import InventoryService
from app.store.memory_store import InMemoryStore

# Las pruebas ejercitan muchos rechazos: se silencia la bitacora para no
# contaminar la salida de pytest (su contenido se verifica en test_req09).
logging.getLogger("inventory").setLevel(logging.CRITICAL)


@pytest.fixture
def app() -> FastAPI:
    """Aplicacion FastAPI nueva e independiente por prueba."""
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Cliente HTTP con el ciclo de vida activo (almacen ya inicializado)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def memory_store() -> InMemoryStore:
    """Almacen en memoria inicializado y aislado de la instancia global."""
    store = InMemoryStore()
    store.initialize()
    return store


@pytest.fixture
def service(memory_store: InMemoryStore) -> InventoryService:
    """Servicio de inventario sobre un almacen aislado."""
    return InventoryService(memory_store)


class LogCapture(logging.Handler):
    """Handler simple para inspeccionar la bitacora del sistema.

    El logger de la aplicacion no propaga al root, por lo que ``caplog`` no lo
    alcanza: estas pruebas se conectan directamente a el.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def text(self) -> str:
        return "\n".join(self.format(record) for record in self.records)


@pytest.fixture
def captured_logs() -> Iterator[LogCapture]:
    """Captura los registros emitidos por el logger ``inventory``."""
    logger = logging.getLogger("inventory")
    handler = LogCapture()
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
