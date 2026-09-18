"""Requerimiento 5: Gestionar Entradas de Stock."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import STOCK_CAPACITY_MAX, STOCK_ENTRY_QUANTITY_MAX
from helpers import create_product, create_product_with_stock

INEXISTENTE = "00000000-0000-4000-8000-000000000000"


def entrada(client: TestClient, product_id: str, quantity) -> "object":
    return client.post(
        "/stock/entries", json={"product_id": product_id, "quantity": quantity}
    )


def test_entrada_valida_incrementa_el_stock(client: TestClient) -> None:
    """Req 5.1: una entrada valida incrementa el Stock_Level y responde 200."""
    creado = create_product(client)

    response = entrada(client, creado["product_id"], 50)

    assert response.status_code == 200
    assert response.json()["stock"] == 50


def test_entrada_sobre_producto_inexistente_responde_404(client: TestClient) -> None:
    """Req 5.2: una entrada a un Product_ID desconocido devuelve 404."""
    response = entrada(client, INEXISTENTE, 10)

    assert response.status_code == 404
    assert response.json()["error_type"] == "not_found"


@pytest.mark.parametrize("quantity", [0, -1, STOCK_ENTRY_QUANTITY_MAX + 1, 1_000_000])
def test_entrada_con_cantidad_fuera_de_rango_responde_400(
    client: TestClient, quantity: int
) -> None:
    """Req 5.3: la cantidad debe estar entre 1 y 999999."""
    creado = create_product(client)

    response = entrada(client, creado["product_id"], quantity)

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


@pytest.mark.parametrize("quantity", [1, STOCK_ENTRY_QUANTITY_MAX])
def test_entrada_en_los_limites_del_rango_es_valida(
    client: TestClient, quantity: int
) -> None:
    """Req 5.3: los extremos 1 y 999999 son validos."""
    creado = create_product(client)

    response = entrada(client, creado["product_id"], quantity)

    assert response.status_code == 200
    assert response.json()["stock"] == quantity


def test_entrada_que_supera_la_capacidad_maxima_responde_400(
    client: TestClient,
) -> None:
    """Req 5.4: si el stock resultante supera 999999 se rechaza la entrada."""
    creado = create_product_with_stock(client, STOCK_CAPACITY_MAX)

    response = entrada(client, creado["product_id"], 1)

    assert response.status_code == 400
    assert "capacidad maxima de stock" in response.json()["message"]
    # El stock no se modifico.
    assert (
        client.get(f"/products/{creado['product_id']}").json()["stock"]
        == STOCK_CAPACITY_MAX
    )


def test_entradas_sucesivas_acumulan_el_stock(client: TestClient) -> None:
    """Req 5.5: el nuevo nivel es el original mas la cantidad ingresada."""
    creado = create_product(client)
    product_id = creado["product_id"]

    assert entrada(client, product_id, 10).json()["stock"] == 10
    assert entrada(client, product_id, 25).json()["stock"] == 35
    assert entrada(client, product_id, 5).json()["stock"] == 40


@pytest.mark.parametrize(
    "payload",
    [
        {"quantity": 10},
        {"product_id": "abc-123"},
        {},
        {"product_id": None, "quantity": 10},
        {"product_id": "abc-123", "quantity": None},
    ],
)
def test_entrada_con_campos_faltantes_responde_400(
    client: TestClient, payload: dict
) -> None:
    """Req 5.6: falta el Product_ID o la cantidad -> 400."""
    response = client.post("/stock/entries", json=payload)

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"
