"""Pruebas basadas en propiedades (Hypothesis).

Ejercitan los invariantes del dominio con entradas generadas, en lugar de
casos puntuales. Operan sobre la capa de servicio para no depender del
transporte HTTP.
"""

import re
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.core.config import (
    DESCRIPTION_CREATE_MAX_LENGTH,
    NAME_MAX_LENGTH,
    PRICE_MAX,
    STOCK_CAPACITY_MAX,
    STOCK_ENTRY_QUANTITY_MAX,
)
from app.core.errors import ValidationError
from app.models.schemas import ProductCreate
from app.models.validators import validate_price, validate_product_id
from app.services.inventory_service import InventoryService
from app.store.memory_store import InMemoryStore

# Texto imprimible sin espacios en los extremos: garantiza valores "con
# significado" segun el Req 1.3.
nombres = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=NAME_MAX_LENGTH,
)
descripciones = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=DESCRIPTION_CREATE_MAX_LENGTH,
)
precios = st.decimals(
    min_value=Decimal("0"),
    max_value=PRICE_MAX,
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

SIN_FIXTURES = settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def nuevo_servicio() -> InventoryService:
    store = InMemoryStore()
    store.initialize()
    return InventoryService(store)


@given(name=nombres, description=descripciones, price=precios)
@SIN_FIXTURES
def test_todo_producto_valido_se_crea_con_stock_cero(
    name: str, description: str, price: Decimal
) -> None:
    """Req 1.6: sin importar los datos, el producto nace con stock en cero."""
    service = nuevo_servicio()

    producto = service.create_product(
        ProductCreate(name=name, description=description, price=price)
    )

    assert producto.stock == 0
    assert producto.name == name.strip()
    assert producto.price == price


@given(name=nombres, description=descripciones, price=precios)
@SIN_FIXTURES
def test_el_product_id_generado_siempre_es_valido(
    name: str, description: str, price: Decimal
) -> None:
    """Req 1.2 y 7.6: el identificador generado pasa su propia validacion."""
    service = nuevo_servicio()

    producto = service.create_product(
        ProductCreate(name=name, description=description, price=price)
    )

    assert validate_product_id(producto.product_id) == producto.product_id


@given(
    entradas=st.lists(
        st.integers(min_value=1, max_value=1000), min_size=1, max_size=20
    )
)
@SIN_FIXTURES
def test_el_stock_es_la_suma_de_las_entradas(entradas: list) -> None:
    """Req 5.5: el Stock_Level equivale a la suma de las entradas aplicadas."""
    service = nuevo_servicio()
    producto = service.create_product(
        ProductCreate(name="Producto", description="Descripcion", price=Decimal("1.00"))
    )

    for cantidad in entradas:
        producto = service.add_stock(producto.product_id, cantidad)

    assert producto.stock == sum(entradas)


@given(
    inicial=st.integers(min_value=1, max_value=10_000),
    salida=st.integers(min_value=1, max_value=10_000),
)
@SIN_FIXTURES
def test_una_salida_nunca_deja_el_stock_negativo(inicial: int, salida: int) -> None:
    """Req 6.1 y 6.3: el Stock_Level jamas queda por debajo de cero."""
    service = nuevo_servicio()
    producto = service.create_product(
        ProductCreate(name="Producto", description="Descripcion", price=Decimal("1.00"))
    )
    producto = service.add_stock(producto.product_id, inicial)

    if salida > inicial:
        with pytest.raises(ValidationError):
            service.remove_stock(producto.product_id, salida)
        # La operacion rechazada no altero el stock (Req 6.3).
        assert service.store.get(producto.product_id).stock == inicial
    else:
        actualizado = service.remove_stock(producto.product_id, salida)
        assert actualizado.stock == inicial - salida

    assert service.store.get(producto.product_id).stock >= 0


@given(cantidad=st.integers(min_value=1, max_value=STOCK_ENTRY_QUANTITY_MAX))
@SIN_FIXTURES
def test_ninguna_entrada_supera_la_capacidad_maxima(cantidad: int) -> None:
    """Req 5.4: el Stock_Level nunca excede la capacidad maxima permitida."""
    service = nuevo_servicio()
    producto = service.create_product(
        ProductCreate(name="Producto", description="Descripcion", price=Decimal("1.00"))
    )

    acumulado = 0
    for _ in range(3):
        try:
            producto = service.add_stock(producto.product_id, cantidad)
            acumulado += cantidad
        except ValidationError:
            break

    assert producto.stock == acumulado
    assert producto.stock <= STOCK_CAPACITY_MAX


@given(precio=precios)
@SIN_FIXTURES
def test_los_precios_validos_sobreviven_al_ciclo_de_validacion(
    precio: Decimal,
) -> None:
    """Req 7.4: validar un precio ya valido es una operacion idempotente."""
    assert validate_price(validate_price(precio)) == precio


# Cualquier texto que NO encaje exactamente con el formato permitido.
identificadores_invalidos = st.text(min_size=1, max_size=60).filter(
    lambda value: re.fullmatch(r"[A-Za-z0-9-]+", value) is None
)


@given(texto=identificadores_invalidos)
@SIN_FIXTURES
def test_los_identificadores_con_caracteres_no_permitidos_se_rechazan(
    texto: str,
) -> None:
    """Req 7.6: solo se admiten caracteres alfanumericos ASCII y guiones."""
    with pytest.raises(ValueError):
        validate_product_id(texto)
