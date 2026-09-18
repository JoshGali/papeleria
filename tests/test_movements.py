"""Historial de movimientos de stock (`GET /stock/movements`).

Extension fuera del documento de requerimientos: registra cada entrada y
salida aplicada para poder responder que se movio y cuando.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import MOVEMENTS_QUERY_MAX_LIMIT
from app.core.errors import ValidationError
from app.models.movement import MovementType
from app.models.schemas import ProductCreate
from app.services.inventory_service import InventoryService
from app.store.memory_store import InMemoryStore
from helpers import MOVEMENT_FIELDS, create_product, create_product_with_stock


def test_una_entrada_deja_asiento_en_el_historial(client: TestClient) -> None:
    """Toda entrada aplicada queda registrada con el antes y el despues."""
    creado = create_product_with_stock(client, 50)

    response = client.get("/stock/movements")

    assert response.status_code == 200
    asientos = response.json()
    assert len(asientos) == 1
    asiento = asientos[0]
    assert set(asiento) == MOVEMENT_FIELDS
    assert asiento["type"] == "entry"
    assert asiento["quantity"] == 50
    assert asiento["stock_before"] == 0
    assert asiento["stock_after"] == 50
    assert asiento["product_id"] == creado["product_id"]


def test_una_salida_deja_asiento_en_el_historial(client: TestClient) -> None:
    """Toda salida aplicada queda registrada con su sentido correcto."""
    creado = create_product_with_stock(client, 50)
    client.post(
        "/stock/exits", json={"product_id": creado["product_id"], "quantity": 12}
    )

    asiento = client.get("/stock/movements").json()[0]

    assert asiento["type"] == "exit"
    assert asiento["quantity"] == 12
    assert asiento["stock_before"] == 50
    assert asiento["stock_after"] == 38


def test_el_historial_va_del_mas_reciente_al_mas_antiguo(
    client: TestClient,
) -> None:
    """El orden facilita mostrar los ultimos movimientos sin reordenar."""
    creado = create_product(client)
    product_id = creado["product_id"]
    for cantidad in (10, 20, 30):
        client.post(
            "/stock/entries", json={"product_id": product_id, "quantity": cantidad}
        )

    asientos = client.get("/stock/movements").json()

    assert [asiento["quantity"] for asiento in asientos] == [30, 20, 10]


def test_una_operacion_rechazada_no_deja_asiento(client: TestClient) -> None:
    """Req 6.3: si la salida se rechaza, no se registra ningun movimiento."""
    creado = create_product_with_stock(client, 10)

    rechazada = client.post(
        "/stock/exits", json={"product_id": creado["product_id"], "quantity": 999}
    )

    assert rechazada.status_code == 400
    # Solo queda la entrada inicial.
    asientos = client.get("/stock/movements").json()
    assert [asiento["type"] for asiento in asientos] == ["entry"]


def test_el_historial_se_filtra_por_producto(client: TestClient) -> None:
    """El filtro permite ver el kardex de un solo articulo."""
    primero = create_product_with_stock(client, 5, name="Primero")
    segundo = create_product_with_stock(client, 7, name="Segundo")

    asientos = client.get(
        "/stock/movements", params={"product_id": primero["product_id"]}
    ).json()

    assert len(asientos) == 1
    assert asientos[0]["product_id"] == primero["product_id"]
    assert segundo["product_id"] not in [a["product_id"] for a in asientos]


def test_el_historial_sobrevive_a_la_eliminacion_del_producto(
    client: TestClient,
) -> None:
    """Un movimiento es un hecho ocurrido: no se borra con el producto."""
    creado = create_product_with_stock(client, 30, name="Producto descontinuado")

    assert client.delete(f"/products/{creado['product_id']}").status_code == 204

    asientos = client.get("/stock/movements").json()
    assert len(asientos) == 1
    # El nombre guardado mantiene legible el historial.
    assert asientos[0]["product_name"] == "Producto descontinuado"


def test_el_asiento_conserva_el_nombre_del_momento(client: TestClient) -> None:
    """Renombrar el producto no reescribe los asientos ya registrados."""
    creado = create_product(client, name="Nombre original")
    product_id = creado["product_id"]
    client.post("/stock/entries", json={"product_id": product_id, "quantity": 10})
    client.patch(f"/products/{product_id}", json={"name": "Nombre nuevo"})
    client.post("/stock/entries", json={"product_id": product_id, "quantity": 5})

    asientos = client.get("/stock/movements").json()

    assert [a["product_name"] for a in asientos] == ["Nombre nuevo", "Nombre original"]


def test_el_limite_acota_los_asientos_devueltos(client: TestClient) -> None:
    """El parametro 'limit' evita traer un historial enorme de una vez."""
    creado = create_product(client)
    for _ in range(5):
        client.post(
            "/stock/entries", json={"product_id": creado["product_id"], "quantity": 1}
        )

    assert len(client.get("/stock/movements", params={"limit": 2}).json()) == 2


@pytest.mark.parametrize("limit", [0, -1, MOVEMENTS_QUERY_MAX_LIMIT + 1])
def test_un_limite_fuera_de_rango_responde_400(
    client: TestClient, limit: int
) -> None:
    """El limite debe estar entre 1 y el maximo configurado."""
    response = client.get("/stock/movements", params={"limit": limit})

    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "limit"


def test_un_product_id_invalido_responde_400(client: TestClient) -> None:
    """Req 7.6: el filtro tambien valida el formato del identificador."""
    response = client.get("/stock/movements", params={"product_id": "id_invalido"})

    assert response.status_code == 400
    assert response.json()["error_type"] == "validation_error"


def test_sin_movimientos_devuelve_arreglo_vacio(client: TestClient) -> None:
    """Un almacen recien iniciado no tiene historial."""
    response = client.get("/stock/movements")

    assert response.status_code == 200
    assert response.json() == []


def test_el_historial_se_pierde_al_reiniciar(client: TestClient) -> None:
    """Req 10.4: el historial vive en memoria como el resto de los datos."""
    create_product_with_stock(client, 10)
    store = InMemoryStore()
    store.initialize()

    assert store.count_movements() == 0


def test_el_historial_tiene_un_tope_de_asientos() -> None:
    """Al llenarse se descartan los mas antiguos, sin crecer sin limite."""
    store = InMemoryStore(movements_capacity=3)
    store.initialize()
    service = InventoryService(store)
    producto = service.create_product(
        ProductCreate(name="Producto", description="Descripcion", price=Decimal("1.00"))
    )

    for _ in range(5):
        service.add_stock(producto.product_id, 1)

    asientos = store.list_movements()
    assert len(asientos) == 3
    # Sobreviven los tres ultimos: el stock final va de 2 a 5.
    assert [a.stock_after for a in asientos] == [5, 4, 3]


def test_los_movimientos_concurrentes_se_registran_todos(
    service: InventoryService,
) -> None:
    """El asiento se escribe dentro del mismo lock que el cambio de stock."""
    producto = service.create_product(
        ProductCreate(name="Producto", description="Descripcion", price=Decimal("1.00"))
    )

    def surtir(_: int) -> None:
        for _ in range(20):
            service.add_stock(producto.product_id, 1)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(surtir, range(8)))

    asientos = service.store.list_movements(limit=None)
    assert len(asientos) == 160
    assert service.store.get(producto.product_id).stock == 160
    # Cada asiento encadena con el siguiente: no hay huecos ni duplicados.
    niveles = sorted(a.stock_after for a in asientos)
    assert niveles == list(range(1, 161))


def test_el_servicio_rechaza_un_limite_no_entero(service: InventoryService) -> None:
    """La validacion del limite vive en el servicio, no solo en la ruta."""
    with pytest.raises(ValidationError):
        service.list_movements(limit="diez")


def test_el_tipo_de_movimiento_usa_los_valores_del_dominio() -> None:
    """Los valores expuestos coinciden con el enum del dominio."""
    assert MovementType.ENTRY.value == "entry"
    assert MovementType.EXIT.value == "exit"
