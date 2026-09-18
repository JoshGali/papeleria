"""Requerimiento 10: Persistencia en Memoria."""

import threading

import pytest
from fastapi.testclient import TestClient

from app.core.config import STORE_MAX_PRODUCTS
from app.core.errors import StorageCapacityError, StoreNotReadyError
from app.main import create_app
from app.models.product import Product
from app.store.memory_store import InMemoryStore
from helpers import create_product


def nuevo_producto(nombre: str = "Producto") -> Product:
    return Product(name=nombre, description="Descripcion de prueba", price=10)


def test_capacidad_maxima_por_defecto_es_10000() -> None:
    """Req 10.1: el almacen admite como maximo 10000 productos."""
    assert InMemoryStore().capacity == STORE_MAX_PRODUCTS


def test_el_almacen_guarda_los_productos_creados(memory_store: InMemoryStore) -> None:
    """Req 10.1: los productos viven en la estructura en memoria."""
    producto = memory_store.add(nuevo_producto())

    assert memory_store.count() == 1
    assert memory_store.get(producto.product_id) is producto


def test_al_iniciar_el_almacen_esta_vacio() -> None:
    """Req 10.2: al arrancar, el In_Memory_Store contiene cero productos."""
    store = InMemoryStore()
    store.initialize()

    assert store.is_initialized
    assert store.count() == 0
    assert store.list_all() == []


def test_almacen_lleno_rechaza_nuevos_productos() -> None:
    """Req 10.3: alcanzada la capacidad se impide almacenar mas productos."""
    store = InMemoryStore(capacity=3)
    store.initialize()
    for indice in range(3):
        store.add(nuevo_producto(f"Producto {indice}"))

    with pytest.raises(StorageCapacityError) as excinfo:
        store.add(nuevo_producto("Excedente"))

    assert excinfo.value.status_code == 507
    assert store.count() == 3


def test_al_detenerse_se_pierden_los_datos(memory_store: InMemoryStore) -> None:
    """Req 10.4: al detener el sistema el almacen pierde todos los datos."""
    memory_store.add(nuevo_producto())

    memory_store.shutdown()

    assert not memory_store.is_initialized
    assert memory_store.count() == 0


def test_al_reiniciar_el_almacen_vuelve_a_cero(memory_store: InMemoryStore) -> None:
    """Req 10.5: tras reiniciar, el almacen contiene cero productos."""
    memory_store.add(nuevo_producto())
    memory_store.shutdown()

    memory_store.initialize()

    assert memory_store.is_initialized
    assert memory_store.count() == 0


def test_operar_sobre_un_almacen_no_inicializado_falla() -> None:
    """Req 2.6: el almacen sin inicializar rechaza cualquier operacion."""
    store = InMemoryStore()

    with pytest.raises(StoreNotReadyError) as excinfo:
        store.list_all()

    assert excinfo.value.status_code == 503


def test_el_ciclo_de_vida_de_la_aplicacion_reinicia_el_almacen() -> None:
    """Req 10.2-10.5 a nivel de aplicacion: cada arranque parte de cero."""
    app = create_app()

    with TestClient(app) as client:
        create_product(client)
        assert client.get("/health").json()["products"] == 1

    # Nuevo arranque del mismo proceso: el almacen global se reinicializa.
    with TestClient(app) as client:
        assert client.get("/health").json()["products"] == 0


def test_las_escrituras_concurrentes_no_pierden_productos(
    memory_store: InMemoryStore,
) -> None:
    """El lock del almacen protege las inserciones simultaneas."""
    total_hilos = 8
    por_hilo = 50

    def insertar(indice: int) -> None:
        for numero in range(por_hilo):
            memory_store.add(nuevo_producto(f"P-{indice}-{numero}"))

    hilos = [threading.Thread(target=insertar, args=(i,)) for i in range(total_hilos)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert memory_store.count() == total_hilos * por_hilo
