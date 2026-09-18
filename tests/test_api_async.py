"""Pruebas asincronas de extremo a extremo con httpx sobre el transporte ASGI.

Complementan las pruebas sincronas verificando el comportamiento de la API en
el bucle de eventos real y bajo peticiones concurrentes.
"""

import asyncio
from typing import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

BASE_URL = "http://inventario.test"


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Cliente asincrono con el ciclo de vida de la aplicacion ya ejecutado."""
    from app.store.memory_store import store

    store.initialize()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
        yield client
    store.shutdown()


NUEVO_PRODUCTO = {
    "name": "Marcador permanente",
    "description": "Marcador de tinta permanente color negro",
    "price": 18.75,
}


async def test_flujo_completo_del_inventario(async_client: httpx.AsyncClient) -> None:
    """Recorre crear, surtir, consultar, vender, actualizar y eliminar."""
    creado = await async_client.post("/products", json=NUEVO_PRODUCTO)
    assert creado.status_code == 201
    product_id = creado.json()["product_id"]

    entrada = await async_client.post(
        "/stock/entries", json={"product_id": product_id, "quantity": 200}
    )
    assert entrada.json()["stock"] == 200

    consulta = await async_client.get(f"/products/{product_id}")
    assert consulta.status_code == 200

    venta = await async_client.post(
        "/stock/exits", json={"product_id": product_id, "quantity": 75}
    )
    assert venta.json()["stock"] == 125

    actualizado = await async_client.patch(
        f"/products/{product_id}", json={"price": 19.99}
    )
    assert actualizado.json()["price"] == 19.99
    assert actualizado.json()["stock"] == 125

    eliminado = await async_client.delete(f"/products/{product_id}")
    assert eliminado.status_code == 204

    assert (await async_client.get(f"/products/{product_id}")).status_code == 404


async def test_creaciones_concurrentes_generan_identificadores_unicos(
    async_client: httpx.AsyncClient,
) -> None:
    """Varias creaciones simultaneas no colisionan ni pierden productos."""
    respuestas = await asyncio.gather(
        *(async_client.post("/products", json=NUEVO_PRODUCTO) for _ in range(30))
    )

    assert all(respuesta.status_code == 201 for respuesta in respuestas)
    identificadores = {respuesta.json()["product_id"] for respuesta in respuestas}
    assert len(identificadores) == 30


async def test_salidas_concurrentes_no_sobregiran_el_stock(
    async_client: httpx.AsyncClient,
) -> None:
    """Diez salidas de 10 unidades sobre un stock de 50: solo 5 pueden aplicarse."""
    creado = await async_client.post("/products", json=NUEVO_PRODUCTO)
    product_id = creado.json()["product_id"]
    await async_client.post(
        "/stock/entries", json={"product_id": product_id, "quantity": 50}
    )

    respuestas = await asyncio.gather(
        *(
            async_client.post(
                "/stock/exits", json={"product_id": product_id, "quantity": 10}
            )
            for _ in range(10)
        )
    )

    exitosas = [r for r in respuestas if r.status_code == 200]
    rechazadas = [r for r in respuestas if r.status_code == 400]
    assert len(exitosas) == 5
    assert len(rechazadas) == 5

    # Con el stock agotado el producto deja de ser consultable (Req 2.3), por
    # lo que el nivel final se verifica con el listado de stock bajo.
    assert (await async_client.get(f"/products/{product_id}")).status_code == 404
    bajos = await async_client.get("/stock/low", params={"threshold": 1})
    assert [p["stock"] for p in bajos.json()] == [0]


async def test_la_documentacion_openapi_esta_disponible(
    async_client: httpx.AsyncClient,
) -> None:
    """El esquema OpenAPI describe todos los endpoints publicados."""
    respuesta = await async_client.get("/openapi.json")

    assert respuesta.status_code == 200
    rutas = respuesta.json()["paths"]
    assert {
        "/products",
        "/products/{product_id}",
        "/stock/entries",
        "/stock/exits",
        "/stock/available",
        "/stock/low",
        "/health",
    } <= set(rutas)
