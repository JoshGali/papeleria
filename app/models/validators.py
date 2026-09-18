"""Validadores reutilizables de los campos del dominio (Requerimiento 7).

Todos los validadores lanzan ``ValueError`` con un mensaje descriptivo. Al
usarse dentro de modelos Pydantic, ese error se convierte en un
``RequestValidationError`` que el manejador global traduce a una respuesta 400
con el formato del Requerimiento 9.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.config import (
    NAME_MAX_LENGTH,
    PRICE_MAX,
    PRICE_MAX_DECIMAL_PLACES,
    PRICE_MIN,
    PRODUCT_ID_MAX_LENGTH,
    PRODUCT_ID_PATTERN,
)

_PRODUCT_ID_RE = re.compile(PRODUCT_ID_PATTERN)


def validate_name(value: Any) -> str:
    """Req 7.2 y 7.7: string no vacio de maximo 200 caracteres."""
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError("El nombre debe ser de tipo string")
    if not value.strip():
        raise ValueError("El nombre no puede estar vacio")
    if len(value) > NAME_MAX_LENGTH:
        raise ValueError(
            f"El nombre no puede exceder {NAME_MAX_LENGTH} caracteres"
        )
    return value.strip()


def validate_description(value: Any, max_length: int) -> str:
    """Req 7.3 y 7.8: string con un limite de longitud segun la operacion.

    Req 1.3 exige ademas que los campos presentes tengan valores
    significativos, por lo que una descripcion en blanco se rechaza.
    """
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError("La descripcion debe ser de tipo string")
    if not value.strip():
        raise ValueError("La descripcion no puede estar vacia")
    if len(value) > max_length:
        raise ValueError(
            f"La descripcion no puede exceder {max_length} caracteres"
        )
    return value.strip()


def validate_price(value: Any) -> Decimal:
    """Req 7.4 y 7.9: numerico, no negativo, <= 999999999.99 y <= 2 decimales."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("El precio debe ser de tipo numerico")
    try:
        price = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("El precio debe ser de tipo numerico") from None
    if not price.is_finite():
        raise ValueError("El precio debe ser un numero finito")
    if price < PRICE_MIN:
        raise ValueError("El precio no puede ser negativo")
    if price > PRICE_MAX:
        raise ValueError(f"El precio no puede exceder {PRICE_MAX}")
    exponent = price.normalize().as_tuple().exponent
    if isinstance(exponent, int) and exponent < -PRICE_MAX_DECIMAL_PLACES:
        raise ValueError(
            f"El precio admite maximo {PRICE_MAX_DECIMAL_PLACES} decimales"
        )
    return price


def validate_quantity(value: Any, *, minimum: int, maximum: int) -> int:
    """Req 7.5 y 7.10: entero dentro del rango permitido por la operacion."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("La cantidad debe ser un numero entero")
    if value < minimum:
        raise ValueError(f"La cantidad debe ser mayor o igual a {minimum}")
    if value > maximum:
        raise ValueError(f"La cantidad no puede exceder {maximum}")
    return value


def validate_product_id(value: Any) -> str:
    """Req 7.6 y 7.11: string alfanumerico con guiones, de 1 a 50 caracteres."""
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError("El Product_ID debe ser de tipo string")
    if not value:
        raise ValueError("El Product_ID no puede estar vacio")
    if len(value) > PRODUCT_ID_MAX_LENGTH:
        raise ValueError(
            f"El Product_ID no puede exceder {PRODUCT_ID_MAX_LENGTH} caracteres"
        )
    if not _PRODUCT_ID_RE.match(value):
        raise ValueError(
            "El Product_ID solo admite caracteres alfanumericos y guiones"
        )
    return value
