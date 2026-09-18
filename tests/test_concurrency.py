"""Pruebas de concurrencia sobre los movimientos de stock.

FastAPI ejecuta los endpoints sincronos en un pool de hilos, por lo que dos
movimientos simultaneos sobre el mismo producto compiten realmente. El ciclo
leer-calcular-escribir del servicio debe ser atomico para no perder
actualizaciones.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from app.core.errors import ValidationError
from app.models.schemas import ProductCreate
from app.services.inventory_service import InventoryService

NUEVO = ProductCreate(
    name="Resma de papel",
    description="Resma de papel bond carta con 500 hojas",
    price=Decimal("89.90"),
)


def test_entradas_simultaneas_no_pierden_unidades(service: InventoryService) -> None:
    """Req 5.5: el total refleja todas las entradas, sin actualizaciones perdidas."""
    producto = service.create_product(NUEVO)
    hilos, por_hilo, cantidad = 8, 25, 3

    def surtir() -> None:
        for _ in range(por_hilo):
            service.add_stock(producto.product_id, cantidad)

    with ThreadPoolExecutor(max_workers=hilos) as pool:
        list(pool.map(lambda _: surtir(), range(hilos)))

    esperado = hilos * por_hilo * cantidad
    assert service.store.get(producto.product_id).stock == esperado


def test_salidas_simultaneas_nunca_sobregiran_el_stock(
    service: InventoryService,
) -> None:
    """Req 6.3: solo se aplican las salidas que caben en el stock disponible."""
    producto = service.create_product(NUEVO)
    service.add_stock(producto.product_id, 100)

    def vender() -> bool:
        try:
            service.remove_stock(producto.product_id, 10)
            return True
        except ValidationError:
            return False

    with ThreadPoolExecutor(max_workers=16) as pool:
        resultados = list(pool.map(lambda _: vender(), range(30)))

    assert sum(resultados) == 10
    assert service.store.get(producto.product_id).stock == 0


def test_entradas_y_salidas_mezcladas_mantienen_el_balance(
    service: InventoryService,
) -> None:
    """El stock final coincide con el balance de las operaciones aplicadas."""
    producto = service.create_product(NUEVO)
    service.add_stock(producto.product_id, 500)

    def operar(indice: int) -> int:
        if indice % 2 == 0:
            service.add_stock(producto.product_id, 4)
            return 4
        service.remove_stock(producto.product_id, 2)
        return -2

    with ThreadPoolExecutor(max_workers=12) as pool:
        balance = sum(pool.map(operar, range(60)))

    assert service.store.get(producto.product_id).stock == 500 + balance
