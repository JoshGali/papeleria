"""Requerimiento 1: Crear Productos."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import (
    DESCRIPTION_CREATE_MAX_LENGTH,
    NAME_MAX_LENGTH,
    PRODUCT_ID_GENERATED_MAX_LENGTH,
)
from app.store.memory_store import InMemoryStore
from helpers import create_product, product_payload, use_store


def test_crear_producto_valido_responde_201_con_product_id(client: TestClient) -> None:
    """Req 1.1: creacion valida devuelve 201 y los datos con su Product_ID."""
    response = client.post("/products", json=product_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Cuaderno profesional"
    assert body["description"] == "Cuaderno de 100 hojas cuadricula chica"
    assert body["price"] == 25.50
    assert body["product_id"]


def test_product_id_es_unico_y_no_excede_100_caracteres(client: TestClient) -> None:
    """Req 1.2: el sistema asigna un Product_ID unico de maximo 100 caracteres."""
    ids = {create_product(client)["product_id"] for _ in range(25)}

    assert len(ids) == 25
    assert all(len(product_id) <= PRODUCT_ID_GENERATED_MAX_LENGTH for product_id in ids)


@pytest.mark.parametrize("missing", ["name", "description", "price"])
def test_campo_obligatorio_faltante_responde_400(
    client: TestClient, missing: str
) -> None:
    """Req 1.3: falta un campo obligatorio -> 400 con el detalle del error."""
    payload = product_payload()
    payload.pop(missing)

    response = client.post("/products", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error_type"] == "validation_error"
    assert any(error["field"] == missing for error in body["errors"])


def test_campos_faltantes_y_presentes_invalidos_se_reportan_juntos(
    client: TestClient,
) -> None:
    """Req 1.3: los campos presentes tambien se validan aunque falten otros."""
    response = client.post("/products", json={"name": "   ", "price": 10.0})

    assert response.status_code == 400
    errores = {error["field"] for error in response.json()["errors"]}
    assert errores == {"name", "description"}


def test_nombre_mayor_a_200_caracteres_responde_400(client: TestClient) -> None:
    """Req 1.4: nombre de mas de 200 caracteres -> 400."""
    response = client.post(
        "/products", json=product_payload(name="A" * (NAME_MAX_LENGTH + 1))
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "name"


def test_nombre_de_exactamente_200_caracteres_es_valido(client: TestClient) -> None:
    """Req 1.4: el limite de 200 caracteres es inclusivo."""
    response = client.post("/products", json=product_payload(name="A" * NAME_MAX_LENGTH))

    assert response.status_code == 201


def test_descripcion_mayor_a_500_caracteres_responde_400(client: TestClient) -> None:
    """Req 1.5: descripcion de mas de 500 caracteres -> 400."""
    response = client.post(
        "/products",
        json=product_payload(description="B" * (DESCRIPTION_CREATE_MAX_LENGTH + 1)),
    )

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "description"


def test_descripcion_de_exactamente_500_caracteres_es_valida(
    client: TestClient,
) -> None:
    """Req 1.5: el limite de 500 caracteres es inclusivo."""
    response = client.post(
        "/products",
        json=product_payload(description="B" * DESCRIPTION_CREATE_MAX_LENGTH),
    )

    assert response.status_code == 201


def test_producto_nuevo_inicia_con_stock_en_cero(client: TestClient) -> None:
    """Req 1.6: todo producto se crea con Stock_Level en cero."""
    assert create_product(client)["stock"] == 0


def test_no_se_admite_fijar_stock_en_la_creacion(client: TestClient) -> None:
    """Req 1.6: el stock inicial no es configurable por el cliente."""
    response = client.post("/products", json=product_payload(stock=50))

    assert response.status_code == 400


def test_almacen_lleno_responde_507(app, client: TestClient) -> None:
    """Req 10.3: sin capacidad disponible la creacion responde 507."""
    pequeno = InMemoryStore(capacity=2)
    pequeno.initialize()
    use_store(app, pequeno)

    assert client.post("/products", json=product_payload()).status_code == 201
    assert client.post("/products", json=product_payload()).status_code == 201

    response = client.post("/products", json=product_payload())

    assert response.status_code == 507
    assert response.json()["error_type"] == "storage_capacity_exceeded"
    # El producto rechazado no se almaceno.
    assert pequeno.count() == 2
