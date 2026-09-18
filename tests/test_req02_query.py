"""Requerimiento 2: Consultar Productos."""

import time

from fastapi.testclient import TestClient

from app.store.memory_store import InMemoryStore
from helpers import create_product, create_product_with_stock, use_store

RESPONSE_FIELDS = {"product_id", "name", "description", "price", "stock"}


def test_consultar_producto_existente_devuelve_datos_completos(
    client: TestClient,
) -> None:
    """Req 2.1: producto con stock y precio no nulos -> 200 en menos de 2 s."""
    creado = create_product_with_stock(client, 15)

    inicio = time.perf_counter()
    response = client.get(f"/products/{creado['product_id']}")
    transcurrido = time.perf_counter() - inicio

    assert response.status_code == 200
    assert transcurrido < 2
    body = response.json()
    assert set(body) == RESPONSE_FIELDS
    assert body["product_id"] == creado["product_id"]
    assert body["stock"] == 15
    assert body["price"] == 25.50


def test_consultar_producto_inexistente_responde_404(client: TestClient) -> None:
    """Req 2.2: un Product_ID desconocido devuelve 404."""
    response = client.get("/products/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["error_type"] == "not_found"


def test_producto_con_stock_cero_se_filtra(client: TestClient) -> None:
    """Req 2.3: stock en cero -> el producto se filtra y responde 404."""
    creado = create_product(client)

    assert client.get(f"/products/{creado['product_id']}").status_code == 404


def test_producto_con_precio_cero_se_filtra(client: TestClient) -> None:
    """Req 2.3: precio en cero -> el producto se filtra y responde 404."""
    creado = create_product_with_stock(client, 10, price=0)

    assert client.get(f"/products/{creado['product_id']}").status_code == 404


def test_listado_devuelve_solo_productos_con_stock_y_precio(
    client: TestClient,
) -> None:
    """Req 2.4: la lista incluye unicamente los productos consultables."""
    visible = create_product_with_stock(client, 5, name="Con stock")
    create_product(client, name="Sin stock")
    create_product_with_stock(client, 5, name="Precio cero", price=0)

    inicio = time.perf_counter()
    response = client.get("/products")
    transcurrido = time.perf_counter() - inicio

    assert response.status_code == 200
    assert transcurrido < 5
    body = response.json()
    assert [p["product_id"] for p in body] == [visible["product_id"]]


def test_listado_con_almacen_vacio_devuelve_arreglo_vacio(
    client: TestClient,
) -> None:
    """Req 2.5: almacen inicializado y vacio -> 200 con arreglo vacio."""
    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


def test_listado_con_almacen_no_inicializado_responde_503(
    app, client: TestClient
) -> None:
    """Req 2.6: el almacen sin inicializar responde 503."""
    sin_inicializar = InMemoryStore()
    use_store(app, sin_inicializar)

    response = client.get("/products")

    assert response.status_code == 503
    assert response.json()["error_type"] == "service_unavailable"
    assert len(response.json()["message"]) >= 10


def test_formato_json_consistente_entre_listado_y_detalle(
    client: TestClient,
) -> None:
    """Req 2.7: el detalle y el listado comparten el mismo formato JSON."""
    creado = create_product_with_stock(client, 7)

    detalle = client.get(f"/products/{creado['product_id']}").json()
    listado = client.get("/products").json()

    assert set(detalle) == RESPONSE_FIELDS
    assert all(set(item) == RESPONSE_FIELDS for item in listado)
    assert listado[0] == detalle
