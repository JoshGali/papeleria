"""Vista de administracion del catalogo (`GET /products?include_unavailable=true`).

Extension fuera del documento de requerimientos: el filtro del Req 2.4 oculta
los productos agotados o sin precio, por lo que una pantalla de administracion
no podria verlos. El parametro levanta ese filtro sin alterar la respuesta por
defecto.
"""

import pytest
from fastapi.testclient import TestClient

from app.store.memory_store import InMemoryStore
from helpers import create_product, create_product_with_stock, use_store

RESPONSE_FIELDS = {"product_id", "name", "description", "price", "stock"}


def test_por_defecto_se_mantiene_el_filtro_del_requerimiento(
    client: TestClient,
) -> None:
    """Req 2.4: sin el parametro, el comportamiento no cambia."""
    visible = create_product_with_stock(client, 5, name="Con stock")
    create_product(client, name="Agotado")
    create_product_with_stock(client, 5, name="Sin precio", price=0)

    response = client.get("/products")

    assert response.status_code == 200
    assert [p["product_id"] for p in response.json()] == [visible["product_id"]]


def test_la_vista_de_administracion_incluye_agotados_y_sin_precio(
    client: TestClient,
) -> None:
    """Con el parametro activo se devuelven todos los productos del almacen."""
    con_stock = create_product_with_stock(client, 5, name="Con stock")
    agotado = create_product(client, name="Agotado")
    sin_precio = create_product_with_stock(client, 5, name="Sin precio", price=0)

    response = client.get("/products", params={"include_unavailable": "true"})

    assert response.status_code == 200
    devueltos = [p["product_id"] for p in response.json()]
    assert devueltos == [
        con_stock["product_id"],
        agotado["product_id"],
        sin_precio["product_id"],
    ]


def test_un_producto_recien_creado_aparece_en_la_vista_de_administracion(
    client: TestClient,
) -> None:
    """El caso que motiva el parametro: dar de alta y seguir viendo el producto."""
    creado = create_product(client, name="Recien dado de alta")

    assert client.get("/products").json() == []
    administrativo = client.get("/products", params={"include_unavailable": "true"})
    assert [p["product_id"] for p in administrativo.json()] == [creado["product_id"]]


@pytest.mark.parametrize("valor", ["false", "0", "False"])
def test_los_valores_falsos_conservan_el_filtro(
    client: TestClient, valor: str
) -> None:
    """Un valor falso equivale a omitir el parametro."""
    create_product(client, name="Agotado")

    assert client.get("/products", params={"include_unavailable": valor}).json() == []


def test_el_formato_de_la_respuesta_no_cambia(client: TestClient) -> None:
    """Req 2.7: la vista administrativa usa el mismo formato JSON."""
    create_product(client, name="Agotado")

    response = client.get("/products", params={"include_unavailable": "true"})

    assert all(set(item) == RESPONSE_FIELDS for item in response.json())


def test_un_valor_no_booleano_responde_400(client: TestClient) -> None:
    """Req 7: un parametro con tipo invalido se rechaza con 400."""
    response = client.get("/products", params={"include_unavailable": "quizas"})

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


def test_el_almacen_no_inicializado_sigue_respondiendo_503(
    app, client: TestClient
) -> None:
    """Req 2.6: la vista administrativa respeta el estado del almacen."""
    use_store(app, InMemoryStore())

    response = client.get("/products", params={"include_unavailable": "true"})

    assert response.status_code == 503
    assert response.json()["error_type"] == "service_unavailable"


def test_con_el_almacen_vacio_devuelve_arreglo_vacio(client: TestClient) -> None:
    """Req 2.5: sin productos la respuesta es un arreglo vacio."""
    response = client.get("/products", params={"include_unavailable": "true"})

    assert response.status_code == 200
    assert response.json() == []
