"""Requerimiento 8: Consultar Disponibilidad de Stock."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import LOW_STOCK_THRESHOLD_MAX, LOW_STOCK_THRESHOLD_MIN
from helpers import create_product, create_product_with_stock

RESPONSE_FIELDS = {"product_id", "name", "description", "price", "stock"}


def test_productos_con_stock_disponible(client: TestClient) -> None:
    """Req 8.1: se devuelven los productos con Stock_Level mayor a cero."""
    con_stock = create_product_with_stock(client, 5, name="Con existencias")
    create_product(client, name="Sin existencias")

    response = client.get("/stock/available")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert [p["product_id"] for p in body] == [con_stock["product_id"]]


def test_productos_con_stock_bajo_segun_umbral(client: TestClient) -> None:
    """Req 8.2: se devuelven los productos con Stock_Level menor o igual al umbral."""
    bajo = create_product_with_stock(client, 3, name="Stock bajo")
    create_product_with_stock(client, 50, name="Stock alto")

    response = client.get("/stock/low", params={"threshold": 5})

    assert response.status_code == 200
    assert [p["product_id"] for p in response.json()] == [bajo["product_id"]]


def test_stock_bajo_incluye_el_valor_exacto_del_umbral(client: TestClient) -> None:
    """Req 8.2: la comparacion es 'menor o igual' al umbral."""
    exacto = create_product_with_stock(client, 10, name="Justo en el umbral")

    response = client.get("/stock/low", params={"threshold": 10})

    assert [p["product_id"] for p in response.json()] == [exacto["product_id"]]


def test_stock_bajo_sin_umbral_responde_400(client: TestClient) -> None:
    """Req 8.3: el umbral es obligatorio."""
    response = client.get("/stock/low")

    assert response.status_code == 400
    body = response.json()
    assert body["error_type"] == "validation_error"
    assert body["errors"][0]["field"] == "threshold"


@pytest.mark.parametrize(
    "threshold",
    [0, -1, LOW_STOCK_THRESHOLD_MAX + 1, 999999],
)
def test_stock_bajo_con_umbral_fuera_de_rango_responde_400(
    client: TestClient, threshold: int
) -> None:
    """Req 8.4: el umbral debe estar entre 1 y 10000 unidades."""
    response = client.get("/stock/low", params={"threshold": threshold})

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


@pytest.mark.parametrize(
    "threshold", [LOW_STOCK_THRESHOLD_MIN, LOW_STOCK_THRESHOLD_MAX]
)
def test_stock_bajo_acepta_los_extremos_del_rango(
    client: TestClient, threshold: int
) -> None:
    """Req 8.4: los extremos 1 y 10000 son validos."""
    assert client.get("/stock/low", params={"threshold": threshold}).status_code == 200


def test_stock_bajo_con_umbral_no_numerico_responde_400(client: TestClient) -> None:
    """Req 8.4: un umbral no numerico tambien se rechaza con 400."""
    response = client.get("/stock/low", params={"threshold": "diez"})

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


def test_filtros_sin_coincidencias_devuelven_arreglo_vacio(
    client: TestClient,
) -> None:
    """Req 8.5: sin coincidencias se devuelve un arreglo vacio con 200."""
    create_product_with_stock(client, 500, name="Bien surtido")

    disponibles = client.get("/stock/available")
    bajos = client.get("/stock/low", params={"threshold": 10})

    assert disponibles.status_code == 200
    assert bajos.status_code == 200
    assert bajos.json() == []


def test_los_filtros_comparten_el_formato_del_listado_completo(
    client: TestClient,
) -> None:
    """Req 8.6: los listados filtrados usan el mismo formato JSON."""
    create_product_with_stock(client, 4)

    completo = client.get("/products").json()
    disponibles = client.get("/stock/available").json()
    bajos = client.get("/stock/low", params={"threshold": 10}).json()

    for coleccion in (completo, disponibles, bajos):
        assert isinstance(coleccion, list)
        assert all(set(item) == RESPONSE_FIELDS for item in coleccion)
    assert completo == disponibles == bajos


def test_stock_bajo_incluye_productos_sin_existencias(client: TestClient) -> None:
    """Req 8.2: un producto agotado tambien esta por debajo del umbral."""
    agotado = create_product(client, name="Agotado")

    response = client.get("/stock/low", params={"threshold": 1})

    assert [p["product_id"] for p in response.json()] == [agotado["product_id"]]
