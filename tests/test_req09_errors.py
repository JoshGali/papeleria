"""Requerimiento 9: Manejo de Errores."""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import ConflictError, build_error_payload
from app.core.middleware import TimeoutAndErrorMiddleware
from app.main import create_app
from app.models.product import Product
from app.store.memory_store import InMemoryStore
from helpers import create_product, product_payload

CAMPOS_OBLIGATORIOS = {"error_type", "message", "status_code"}


def assert_formato_de_error(body: dict, error_type: str, status_code: int) -> None:
    """Verifica el contrato comun de error (Req 9.1-9.3)."""
    assert CAMPOS_OBLIGATORIOS <= set(body)
    assert body["error_type"] == error_type
    assert body["status_code"] == status_code
    assert 10 <= len(body["message"]) <= 200


def test_error_de_validacion_usa_el_formato_estandar(client: TestClient) -> None:
    """Req 9.1: error de validacion -> error_type 'validation_error'."""
    response = client.post("/products", json=product_payload(price=-1))

    assert response.status_code == 400
    assert_formato_de_error(response.json(), "validation_error", 400)


def test_error_de_recurso_no_encontrado_usa_el_formato_estandar(
    client: TestClient,
) -> None:
    """Req 9.2: recurso inexistente -> error_type 'not_found'."""
    response = client.get("/products/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert_formato_de_error(response.json(), "not_found", 404)


def test_error_de_conflicto_usa_el_formato_estandar() -> None:
    """Req 9.3: recurso duplicado -> error_type 'conflict' con 409."""
    store = InMemoryStore()
    store.initialize()
    producto = Product(name="Goma", description="Goma blanca", price=5)
    store.add(producto)

    with pytest.raises(ConflictError) as excinfo:
        store.add(producto)

    assert_formato_de_error(excinfo.value.to_payload(), "conflict", 409)


def test_varios_errores_de_validacion_se_devuelven_en_un_arreglo(
    client: TestClient,
) -> None:
    """Req 9.4: todos los errores de la peticion viajan en 'errors'."""
    response = client.post("/products", json={"name": "", "description": 5, "price": "x"})

    assert response.status_code == 400
    body = response.json()
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) == 3
    assert {error["field"] for error in body["errors"]} == {
        "name",
        "description",
        "price",
    }
    for error in body["errors"]:
        assert {"field", "message", "type"} <= set(error)


def test_excepcion_no_controlada_responde_500() -> None:
    """Req 9.5: un fallo inesperado devuelve 500 sin filtrar detalles."""
    app = create_app()

    @app.get("/__boom")
    def boom() -> None:
        raise RuntimeError("fallo interno simulado")

    with TestClient(app) as client:
        response = client.get("/__boom")

    assert response.status_code == 500
    body = response.json()
    assert_formato_de_error(body, "internal_error", 500)
    assert body["message"] == "An internal error occurred"
    assert "fallo interno simulado" not in response.text


def test_peticion_que_excede_el_tiempo_limite_responde_504() -> None:
    """Req 9.6: una peticion que no termina a tiempo devuelve 504."""
    app = create_app()

    @app.get("/__lento")
    async def lento() -> dict:
        await asyncio.sleep(2)
        return {"status": "nunca llega"}

    # Middleware externo con un limite corto: reproduce el vencimiento sin
    # esperar los 30 segundos de produccion.
    app.add_middleware(TimeoutAndErrorMiddleware, timeout_seconds=0.1)

    with TestClient(app) as client:
        response = client.get("/__lento")

    assert response.status_code == 504
    assert_formato_de_error(response.json(), "timeout", 504)


def test_metodo_http_no_soportado_responde_405(client: TestClient) -> None:
    """Req 9.7: un metodo no permitido devuelve 405."""
    response = client.request("PATCH", "/products")

    assert response.status_code == 405
    assert_formato_de_error(response.json(), "method_not_allowed", 405)


def test_ruta_inexistente_responde_404_con_el_formato_estandar(
    client: TestClient,
) -> None:
    """Una ruta desconocida tambien respeta el contrato de error."""
    response = client.get("/ruta/que/no/existe")

    assert response.status_code == 404
    assert_formato_de_error(response.json(), "not_found", 404)


def test_los_errores_se_registran_con_contexto(
    client: TestClient, captured_logs
) -> None:
    """Req 9.8: se registra timestamp, ruta, metodo y detalle del error."""
    client.get("/products/00000000-0000-4000-8000-000000000000")

    registro = captured_logs.text()
    assert "error_type=not_found" in registro
    assert "method=GET" in registro
    assert "path=/products/00000000-0000-4000-8000-000000000000" in registro
    # El formateador antepone el timestamp ISO-8601 de cada registro.
    assert captured_logs.records[0].created > 0


@pytest.mark.parametrize(
    "mensaje",
    ["corto", "", "M" * 500],
    ids=["muy-corto", "vacio", "muy-largo"],
)
def test_los_mensajes_siempre_respetan_el_rango_permitido(mensaje: str) -> None:
    """Req 9.1-9.3: el mensaje siempre mide entre 10 y 200 caracteres."""
    payload = build_error_payload(
        error_type="validation_error", message=mensaje, status_code=400
    )

    assert 10 <= len(payload["message"]) <= 200


def test_todos_los_errores_de_la_api_comparten_el_contrato(
    app: FastAPI, client: TestClient
) -> None:
    """Recorre los principales caminos de error y valida el formato comun."""
    creado = create_product(client)
    casos = [
        (client.post("/products", json={}), 400),
        (client.get("/products/inexistente-0000"), 404),
        (client.delete("/products/id_malo"), 400),
        (client.patch(f"/products/{creado['product_id']}", json={}), 400),
        (client.get("/stock/low"), 400),
        (client.request("PUT", "/stock/available"), 405),
    ]

    for response, esperado in casos:
        assert response.status_code == esperado, response.text
        body = response.json()
        assert CAMPOS_OBLIGATORIOS <= set(body)
        assert body["status_code"] == esperado
        assert 10 <= len(body["message"]) <= 200
