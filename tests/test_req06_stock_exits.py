"""Requerimiento 6: Gestionar Salidas de Stock."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import STOCK_EXIT_QUANTITY_MAX
from helpers import create_product, create_product_with_stock

INEXISTENTE = "00000000-0000-4000-8000-000000000000"


def salida(client: TestClient, product_id: str, quantity) -> "object":
    return client.post(
        "/stock/exits", json={"product_id": product_id, "quantity": quantity}
    )


def test_salida_valida_descuenta_el_stock(client: TestClient) -> None:
    """Req 6.1: con existencias suficientes se descuenta y responde 200."""
    creado = create_product_with_stock(client, 100)

    response = salida(client, creado["product_id"], 30)

    assert response.status_code == 200
    assert response.json()["stock"] == 70


def test_salida_exacta_deja_el_stock_en_cero(client: TestClient) -> None:
    """Req 6.1: retirar todas las existencias es valido."""
    creado = create_product_with_stock(client, 12)

    response = salida(client, creado["product_id"], 12)

    assert response.status_code == 200
    assert response.json()["stock"] == 0


def test_salida_sobre_producto_inexistente_responde_404(client: TestClient) -> None:
    """Req 6.2: una salida de un Product_ID desconocido devuelve 404."""
    response = salida(client, INEXISTENTE, 5)

    assert response.status_code == 404
    assert response.json()["error_type"] == "not_found"


def test_salida_mayor_al_stock_no_descuenta_nada(client: TestClient) -> None:
    """Req 6.3: cantidad mayor al stock -> 400 y la operacion no se aplica."""
    creado = create_product_with_stock(client, 10)

    response = salida(client, creado["product_id"], 11)

    assert response.status_code == 400
    body = response.json()
    assert body["error_type"] == "validation_error"
    assert "Stock insuficiente" in body["message"]
    assert 10 <= len(body["message"]) <= 200
    # El stock quedo intacto: la operacion se rechaza por completo.
    assert client.get(f"/products/{creado['product_id']}").json()["stock"] == 10


@pytest.mark.parametrize("quantity", [0, -1, STOCK_EXIT_QUANTITY_MAX + 1])
def test_salida_con_cantidad_fuera_de_rango_responde_400(
    client: TestClient, quantity: int
) -> None:
    """Req 6.4: la cantidad debe estar entre 1 y 999999999."""
    creado = create_product_with_stock(client, 10)

    response = salida(client, creado["product_id"], quantity)

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


def test_salida_en_el_limite_superior_del_rango_falla_por_stock(
    client: TestClient,
) -> None:
    """Req 6.4: 999999999 es una cantidad valida; el rechazo viene del stock."""
    creado = create_product_with_stock(client, 10)

    response = salida(client, creado["product_id"], STOCK_EXIT_QUANTITY_MAX)

    assert response.status_code == 400
    assert "Stock insuficiente" in response.json()["message"]


@pytest.mark.parametrize(
    "payload",
    [{"quantity": 5}, {"product_id": "abc-123"}, {}, {"product_id": "abc-123", "quantity": "5"}],
)
def test_salida_con_campos_faltantes_o_invalidos_responde_400(
    client: TestClient, payload: dict
) -> None:
    """Req 6.5: falta el Product_ID o la cantidad -> 400."""
    response = client.post("/stock/exits", json=payload)

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


def test_ciclo_completo_entrada_y_salida(client: TestClient) -> None:
    """Flujo real: se surte el producto y luego se venden unidades."""
    creado = create_product(client, name="Lapiz HB")
    product_id = creado["product_id"]

    client.post("/stock/entries", json={"product_id": product_id, "quantity": 500})
    salida(client, product_id, 120)
    salida(client, product_id, 80)

    assert client.get(f"/products/{product_id}").json()["stock"] == 300
