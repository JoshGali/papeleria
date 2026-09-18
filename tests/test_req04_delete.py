"""Requerimiento 4: Eliminar Productos."""

import pytest
from fastapi.testclient import TestClient

from helpers import create_product, create_product_with_stock

INEXISTENTE = "00000000-0000-4000-8000-000000000000"


def test_eliminar_producto_existente_responde_204(client: TestClient) -> None:
    """Req 4.1: el producto se elimina por completo y responde 204 sin cuerpo."""
    creado = create_product_with_stock(client, 3)

    response = client.delete(f"/products/{creado['product_id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/products").json() == []


def test_eliminar_producto_inexistente_responde_404(client: TestClient) -> None:
    """Req 4.2: eliminar un Product_ID desconocido devuelve 404."""
    response = client.delete(f"/products/{INEXISTENTE}")

    assert response.status_code == 404
    assert response.json()["error_type"] == "not_found"


def test_eliminar_dos_veces_el_mismo_producto_responde_404(
    client: TestClient,
) -> None:
    """Req 4.3: la segunda eliminacion devuelve 404."""
    creado = create_product(client)

    assert client.delete(f"/products/{creado['product_id']}").status_code == 204
    assert client.delete(f"/products/{creado['product_id']}").status_code == 404


# Nota: un "/" no puede probarse aqui porque parte la ruta en dos segmentos y
# la peticion ni siquiera alcanza el endpoint.
@pytest.mark.parametrize(
    "product_id", ["id_con_guion_bajo", "id con espacios", "a" * 51, "id.1", "id%23"]
)
def test_eliminar_con_product_id_invalido_responde_400(
    client: TestClient, product_id: str
) -> None:
    """Req 4.4: un Product_ID con formato invalido devuelve 400, no 404."""
    response = client.delete(f"/products/{product_id}")

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


def test_consultar_despues_de_eliminar_responde_404(client: TestClient) -> None:
    """Req 4.5: tras eliminar, la consulta del producto devuelve 404."""
    creado = create_product_with_stock(client, 6)

    client.delete(f"/products/{creado['product_id']}")

    assert client.get(f"/products/{creado['product_id']}").status_code == 404
