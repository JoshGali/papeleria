"""Requerimiento 7: Validar Datos de Entrada."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    PRICE_MAX,
    PRODUCT_ID_MAX_LENGTH,
    STOCK_LEVEL_MAX,
)
from helpers import create_product, product_payload

JSON_HEADERS = {"content-type": "application/json"}


def test_json_mal_formado_responde_400(client: TestClient) -> None:
    """Req 7.1: un cuerpo que no es JSON valido se rechaza con 400."""
    response = client.post("/products", content=b'{"name": "x",', headers=JSON_HEADERS)

    assert response.status_code == 400
    body = response.json()
    assert body["error_type"] == "validation_error"
    assert "JSON" in body["message"]


def test_json_mal_formado_se_registra_en_bitacora(
    client: TestClient, captured_logs
) -> None:
    """Req 7.1 y 9.8: el rechazo queda registrado con ruta, metodo y detalle."""
    client.post("/products", content=b"{no-json", headers=JSON_HEADERS)

    registro = captured_logs.text()
    assert "status=400" in registro
    assert "path=/products" in registro
    assert "method=POST" in registro


@pytest.mark.parametrize("name", ["", "   ", "N" * (NAME_MAX_LENGTH + 1)])
def test_nombre_invalido_responde_400(client: TestClient, name: str) -> None:
    """Req 7.2: nombre vacio o de mas de 200 caracteres -> 400."""
    response = client.post("/products", json=product_payload(name=name))

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "name"


def test_descripcion_mayor_a_1000_caracteres_en_update_responde_400(
    client: TestClient,
) -> None:
    """Req 7.3: la regla general limita la descripcion a 1000 caracteres."""
    creado = create_product(client)

    response = client.patch(
        f"/products/{creado['product_id']}",
        json={"description": "D" * (DESCRIPTION_MAX_LENGTH + 1)},
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "description"


def test_descripcion_de_1000_caracteres_en_update_es_valida(
    client: TestClient,
) -> None:
    """Req 7.3: el limite general de 1000 caracteres es inclusivo."""
    creado = create_product(client)

    response = client.patch(
        f"/products/{creado['product_id']}",
        json={"description": "D" * DESCRIPTION_MAX_LENGTH},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "price",
    [-0.01, -100, float(PRICE_MAX) * 10, 10.123, 0.001],
    ids=["negativo-decimal", "negativo-entero", "excede-maximo", "3-decimales", "4-decimales"],
)
def test_precio_invalido_responde_400(client: TestClient, price: float) -> None:
    """Req 7.4: precio negativo, excesivo o con mas de 2 decimales -> 400."""
    response = client.post("/products", json=product_payload(price=price))

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "price"


@pytest.mark.parametrize("price", [0, 0.01, 1, 25.5, 999999999.99])
def test_precio_valido_es_aceptado(client: TestClient, price: float) -> None:
    """Req 7.4: los valores dentro del rango permitido se aceptan."""
    response = client.post("/products", json=product_payload(price=price))

    assert response.status_code == 201


@pytest.mark.parametrize("quantity", [-1, STOCK_LEVEL_MAX + 1])
def test_cantidad_de_stock_invalida_responde_400(
    client: TestClient, quantity: int
) -> None:
    """Req 7.5: cantidad negativa o mayor a 2147483647 -> 400."""
    creado = create_product(client)

    response = client.post(
        "/stock/entries",
        json={"product_id": creado["product_id"], "quantity": quantity},
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "product_id",
    ["", "a" * (PRODUCT_ID_MAX_LENGTH + 1), "id_invalido", "id@special", "id 1"],
    ids=["vacio", "muy-largo", "guion-bajo", "caracter-especial", "espacio"],
)
def test_product_id_con_formato_invalido_responde_400(
    client: TestClient, product_id: str
) -> None:
    """Req 7.6: Product_ID vacio, largo o con caracteres no permitidos -> 400."""
    response = client.post(
        "/stock/entries", json={"product_id": product_id, "quantity": 5}
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "product_id"


@pytest.mark.parametrize("name", [123, 12.5, True, None, ["lista"], {"a": 1}])
def test_nombre_con_tipo_incorrecto_responde_400(client: TestClient, name) -> None:
    """Req 7.7: el nombre debe ser de tipo string."""
    response = client.post("/products", json=product_payload(name=name))

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "name"


@pytest.mark.parametrize("description", [123, True, None, ["lista"], {"a": 1}])
def test_descripcion_con_tipo_incorrecto_responde_400(
    client: TestClient, description
) -> None:
    """Req 7.8: la descripcion debe ser de tipo string."""
    response = client.post("/products", json=product_payload(description=description))

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "description"


@pytest.mark.parametrize("price", ["25.50", True, None, ["lista"], {"a": 1}])
def test_precio_con_tipo_incorrecto_responde_400(client: TestClient, price) -> None:
    """Req 7.9: el precio debe ser de tipo numerico (un string no lo es)."""
    response = client.post("/products", json=product_payload(price=price))

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "price"


@pytest.mark.parametrize("quantity", ["10", 10.5, True, None, ["lista"]])
def test_cantidad_con_tipo_incorrecto_responde_400(client: TestClient, quantity) -> None:
    """Req 7.10: la cantidad de stock debe ser un entero."""
    creado = create_product(client)

    response = client.post(
        "/stock/entries",
        json={"product_id": creado["product_id"], "quantity": quantity},
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "quantity"


@pytest.mark.parametrize("product_id", [123, True, None, ["lista"], {"a": 1}])
def test_product_id_con_tipo_incorrecto_responde_400(
    client: TestClient, product_id
) -> None:
    """Req 7.11: el Product_ID debe ser de tipo string."""
    response = client.post(
        "/stock/exits", json={"product_id": product_id, "quantity": 1}
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "product_id"


def test_el_rechazo_bloquea_el_procesamiento(client: TestClient) -> None:
    """Req 7.x: una peticion rechazada no produce ningun efecto en el almacen."""
    client.post("/products", json=product_payload(name=""))
    client.post("/products", json=product_payload(price=-1))
    client.post("/products", content=b"{roto", headers=JSON_HEADERS)

    assert client.get("/health").json()["products"] == 0
