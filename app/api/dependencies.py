"""Dependencias compartidas por los routers de la API."""

from fastapi import Depends

from app.services.inventory_service import InventoryService
from app.store.memory_store import InMemoryStore, store


def get_store() -> InMemoryStore:
    """Devuelve el In_Memory_Store de la aplicacion (Req 10)."""
    return store


def get_inventory_service(
    current_store: InMemoryStore = Depends(get_store),
) -> InventoryService:
    """Construye el servicio sobre el almacen vigente.

    Al depender de ``get_store`` la aplicacion puede sustituir el
    almacenamiento (por ejemplo por DynamoDB) sin tocar los endpoints.
    """
    return InventoryService(current_store)
