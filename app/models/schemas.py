"""Esquemas Pydantic de entrada y salida de la API REST.

Los limites de cada campo viven en ``app.models.validators`` para que las
reglas del Requerimiento 7 sean unicas y compartidas por todas las
operaciones.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import (
    DESCRIPTION_CREATE_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    STOCK_ENTRY_QUANTITY_MAX,
    STOCK_ENTRY_QUANTITY_MIN,
    STOCK_EXIT_QUANTITY_MAX,
    STOCK_EXIT_QUANTITY_MIN,
)
from app.models.movement import StockMovement
from app.models.product import Product
from app.models.validators import (
    validate_description,
    validate_name,
    validate_price,
    validate_product_id,
    validate_quantity,
)

_STRICT = ConfigDict(extra="forbid", str_strip_whitespace=False)


class ProductCreate(BaseModel):
    """Cuerpo de ``POST /products`` (Req 1).

    Los tres campos son obligatorios; su ausencia produce un 400 con el
    detalle de cada campo faltante (Req 1.3, Req 9.4).
    """

    model_config = _STRICT

    name: Any = Field(..., description=f"Nombre del producto (1-{NAME_MAX_LENGTH})")
    description: Any = Field(
        ..., description=f"Descripcion (1-{DESCRIPTION_CREATE_MAX_LENGTH})"
    )
    price: Any = Field(..., description="Precio unitario, maximo 2 decimales")

    @field_validator("name", mode="before")
    @classmethod
    def _check_name(cls, value: Any) -> str:
        return validate_name(value)

    @field_validator("description", mode="before")
    @classmethod
    def _check_description(cls, value: Any) -> str:
        # Req 1.5: en la creacion el limite es de 500 caracteres.
        return validate_description(value, DESCRIPTION_CREATE_MAX_LENGTH)

    @field_validator("price", mode="before")
    @classmethod
    def _check_price(cls, value: Any) -> Decimal:
        return validate_price(value)


class ProductUpdate(BaseModel):
    """Cuerpo de ``PATCH``/``PUT`` ``/products/{product_id}`` (Req 3).

    Solo se admiten campos actualizables: ``name``, ``description`` y
    ``price``. ``stock`` queda fuera del esquema, por lo que enviarlo produce
    un 400 (Req 3.5).
    """

    model_config = _STRICT

    name: Optional[Any] = None
    description: Optional[Any] = None
    price: Optional[Any] = None

    @field_validator("name", mode="before")
    @classmethod
    def _check_name(cls, value: Any) -> str:
        return validate_name(value)

    @field_validator("description", mode="before")
    @classmethod
    def _check_description(cls, value: Any) -> str:
        # Req 3.3 remite al Req 7.3: el limite general es de 1000 caracteres.
        return validate_description(value, DESCRIPTION_MAX_LENGTH)

    @field_validator("price", mode="before")
    @classmethod
    def _check_price(cls, value: Any) -> Decimal:
        return validate_price(value)

    def provided_changes(self) -> dict:
        """Campos realmente enviados por el cliente (Req 3.6 y 3.8)."""
        return {name: getattr(self, name) for name in self.model_fields_set}


class StockEntryRequest(BaseModel):
    """Cuerpo de ``POST /stock/entries`` (Req 5)."""

    model_config = _STRICT

    product_id: Any = Field(..., description="Identificador del producto")
    quantity: Any = Field(
        ...,
        description=(
            f"Unidades a ingresar "
            f"({STOCK_ENTRY_QUANTITY_MIN}-{STOCK_ENTRY_QUANTITY_MAX})"
        ),
    )

    @field_validator("product_id", mode="before")
    @classmethod
    def _check_product_id(cls, value: Any) -> str:
        return validate_product_id(value)

    @field_validator("quantity", mode="before")
    @classmethod
    def _check_quantity(cls, value: Any) -> int:
        return validate_quantity(
            value,
            minimum=STOCK_ENTRY_QUANTITY_MIN,
            maximum=STOCK_ENTRY_QUANTITY_MAX,
        )


class StockExitRequest(BaseModel):
    """Cuerpo de ``POST /stock/exits`` (Req 6)."""

    model_config = _STRICT

    product_id: Any = Field(..., description="Identificador del producto")
    quantity: Any = Field(
        ...,
        description=(
            f"Unidades a retirar "
            f"({STOCK_EXIT_QUANTITY_MIN}-{STOCK_EXIT_QUANTITY_MAX})"
        ),
    )

    @field_validator("product_id", mode="before")
    @classmethod
    def _check_product_id(cls, value: Any) -> str:
        return validate_product_id(value)

    @field_validator("quantity", mode="before")
    @classmethod
    def _check_quantity(cls, value: Any) -> int:
        return validate_quantity(
            value,
            minimum=STOCK_EXIT_QUANTITY_MIN,
            maximum=STOCK_EXIT_QUANTITY_MAX,
        )


class ProductResponse(BaseModel):
    """Representacion publica de un producto (Req 2.7 y Req 8.6).

    Ademas de los cinco campos que exige el Req 2.7 incluye ``created_at`` y
    ``updated_at``, que la interfaz usa para mostrar el alta y la ultima
    modificacion.
    """

    product_id: str
    name: str
    description: str
    price: float
    stock: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_product(cls, product: Product) -> "ProductResponse":
        return cls(**product.to_dict())


def to_response_list(products: List[Product]) -> List[ProductResponse]:
    """Serializa una coleccion conservando el mismo formato JSON (Req 8.6)."""
    return [ProductResponse.from_product(product) for product in products]


class MovementResponse(BaseModel):
    """Asiento del historial de movimientos de stock."""

    movement_id: str
    product_id: str
    product_name: str
    type: str
    quantity: int
    stock_before: int
    stock_after: int
    created_at: datetime

    @classmethod
    def from_movement(cls, movement: StockMovement) -> "MovementResponse":
        return cls(**movement.to_dict())


def to_movement_list(movements: List[StockMovement]) -> List[MovementResponse]:
    return [MovementResponse.from_movement(movement) for movement in movements]


class ErrorDetail(BaseModel):
    """Error de validacion individual dentro del arreglo ``errors`` (Req 9.4)."""

    field: str
    message: str
    type: str


class ErrorResponse(BaseModel):
    """Formato unico de error de la API (Req 9)."""

    error_type: str
    message: str
    status_code: int
    errors: Optional[List[ErrorDetail]] = None
