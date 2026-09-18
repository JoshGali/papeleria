"""Requerimiento 3: Actualizar Productos."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import DESCRIPTION_MAX_LENGTH
from helpers import create_product, create_product_with_stock

INEXISTENTE = "00000000-0000-4000-8000-000000000000"


def test_actualizar_campos_validos_responde_200(client: TestClient) -> None:
    """Req 3.1: actualizacion valida devuelve 200 con el producto actualizado."""
    creado = create_product_with_stock(client, 4)

    response = client.patch(
        f"/products/{creado['product_id']}",
        json={"name": "Cuaderno italiano", "price": 30.00},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Cuaderno italiano"
    assert body["price"] == 30.00


def test_actualizar_producto_inexistente_responde_404(client: TestClient) -> None:
    """Req 3.2: actualizar un Product_ID desconocido devuelve 404."""
    response = client.patch(f"/products/{INEXISTENTE}", json={"name": "Otro"})

    assert response.status_code == 404
    assert response.json()["error_type"] == "not_found"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": 123},
        {"price": -5},
        {"price": "10"},
        {"price": 10.123},
        {"description": "x" * (DESCRIPTION_MAX_LENGTH + 1)},
    ],
)
def test_actualizar_con_datos_invalidos_responde_400(
    client: TestClient, payload: dict
) -> None:
    """Req 3.3: datos invalidos segun el Req 7 devuelven 400 con detalle."""
    creado = create_product(client)

    response = client.patch(f"/products/{creado['product_id']}", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error_type"] == "validation_error"
    assert body["errors"]


def test_el_product_id_se_conserva_tras_actualizar(client: TestClient) -> None:
    """Req 3.4: la actualizacion nunca cambia el Product_ID."""
    creado = create_product(client)

    response = client.patch(
        f"/products/{creado['product_id']}", json={"name": "Nombre nuevo"}
    )

    assert response.json()["product_id"] == creado["product_id"]


def test_no_se_permite_actualizar_el_stock(client: TestClient) -> None:
    """Req 3.5: el Stock_Level no es actualizable por esta operacion."""
    creado = create_product_with_stock(client, 12)

    response = client.patch(f"/products/{creado['product_id']}", json={"stock": 999})

    assert response.status_code == 400
    # El stock permanece intacto.
    assert client.get(f"/products/{creado['product_id']}").json()["stock"] == 12


def test_actualizar_sin_campos_responde_400(client: TestClient) -> None:
    """Req 3.6: un cuerpo sin campos actualizables devuelve 400."""
    creado = create_product(client)

    response = client.patch(f"/products/{creado['product_id']}", json={})

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


def test_actualizar_con_valores_identicos_responde_400(client: TestClient) -> None:
    """Req 3.7: si ningun valor cambia se rechaza indicando que no hay cambios."""
    creado = create_product(client)

    response = client.patch(
        f"/products/{creado['product_id']}",
        json={"name": creado["name"], "price": creado["price"]},
    )

    assert response.status_code == 400
    assert "identicos" in response.json()["message"]


def test_actualizacion_parcial_solo_modifica_los_campos_distintos(
    client: TestClient,
) -> None:
    """Req 3.8: se modifican solo los campos cuyo valor difiere del actual."""
    creado = create_product_with_stock(client, 9)

    response = client.patch(
        f"/products/{creado['product_id']}",
        json={"name": creado["name"], "price": 99.99},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 99.99
    assert body["name"] == creado["name"]
    assert body["description"] == creado["description"]
    assert body["stock"] == 9


def test_put_es_equivalente_a_patch(client: TestClient) -> None:
    """El alias PUT conserva la semantica parcial del Req 3.8."""
    creado = create_product(client)

    response = client.put(
        f"/products/{creado['product_id']}", json={"description": "Nueva descripcion"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == creado["name"]
    assert response.json()["description"] == "Nueva descripcion"
