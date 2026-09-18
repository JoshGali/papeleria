"""Utilidades de datos compartidas por las pruebas."""

from typing import Any, Dict

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_store
from app.store.memory_store import InMemoryStore

VALID_PRODUCT: Dict[str, Any] = {
    "name": "Cuaderno profesional",
    "description": "Cuaderno de 100 hojas cuadricula chica",
    "price": 25.50,
}


def use_store(app: FastAPI, store: InMemoryStore) -> None:
    """Sustituye el almacen que usan los endpoints (inyeccion de dependencias)."""
    app.dependency_overrides[get_store] = lambda: store


def product_payload(**overrides: Any) -> Dict[str, Any]:
    """Cuerpo valido de creacion con los campos que se deseen sobreescribir."""
    payload = dict(VALID_PRODUCT)
    payload.update(overrides)
    return payload


def create_product(client: TestClient, **overrides: Any) -> Dict[str, Any]:
    """Crea un producto por API y devuelve su representacion."""
    response = client.post("/products", json=product_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def create_product_with_stock(
    client: TestClient, quantity: int, **overrides: Any
) -> Dict[str, Any]:
    """Crea un producto y le registra una entrada de stock inicial."""
    product = create_product(client, **overrides)
    response = client.post(
        "/stock/entries",
        json={"product_id": product["product_id"], "quantity": quantity},
    )
    assert response.status_code == 200, response.text
    return response.json()
