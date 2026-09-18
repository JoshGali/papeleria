"""Endpoints de movimientos y disponibilidad de stock (Req 5, 6 y 8)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_inventory_service
from app.core.config import (
    LOW_STOCK_QUERY_DESCRIPTION,
    MOVEMENTS_QUERY_DEFAULT_LIMIT,
    MOVEMENTS_QUERY_MAX_LIMIT,
)
from app.models.schemas import (
    ErrorResponse,
    MovementResponse,
    ProductResponse,
    StockEntryRequest,
    StockExitRequest,
    to_movement_list,
    to_response_list,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/stock", tags=["Stock"])

_STOCK_ERRORS = {
    400: {"model": ErrorResponse, "description": "Datos de entrada invalidos"},
    404: {"model": ErrorResponse, "description": "Producto no encontrado"},
}


@router.post(
    "/entries",
    response_model=ProductResponse,
    summary="Registrar una entrada de stock",
    responses=_STOCK_ERRORS,
)
def add_stock(
    payload: StockEntryRequest,
    service: InventoryService = Depends(get_inventory_service),
) -> ProductResponse:
    """Req 5: incrementa el Stock_Level y devuelve el producto actualizado."""
    product = service.add_stock(payload.product_id, payload.quantity)
    return ProductResponse.from_product(product)


@router.post(
    "/exits",
    response_model=ProductResponse,
    summary="Registrar una salida de stock",
    responses=_STOCK_ERRORS,
)
def remove_stock(
    payload: StockExitRequest,
    service: InventoryService = Depends(get_inventory_service),
) -> ProductResponse:
    """Req 6: descuenta el Stock_Level solo si hay existencias suficientes."""
    product = service.remove_stock(payload.product_id, payload.quantity)
    return ProductResponse.from_product(product)


@router.get(
    "/available",
    response_model=List[ProductResponse],
    summary="Listar productos con stock disponible",
    responses={
        503: {"model": ErrorResponse, "description": "Almacen no inicializado"},
    },
)
def list_available(
    service: InventoryService = Depends(get_inventory_service),
) -> List[ProductResponse]:
    """Req 8.1: productos cuyo Stock_Level es mayor que cero."""
    return to_response_list(service.list_available_products())


@router.get(
    "/movements",
    response_model=List[MovementResponse],
    summary="Consultar el historial de movimientos",
    responses={
        400: {"model": ErrorResponse, "description": "Parametros invalidos"},
        503: {"model": ErrorResponse, "description": "Almacen no inicializado"},
    },
)
def list_movements(
    product_id: Optional[str] = Query(
        None, description="Filtra el historial por producto"
    ),
    limit: Optional[int] = Query(
        None,
        description=(
            f"Maximo de asientos a devolver (1-{MOVEMENTS_QUERY_MAX_LIMIT}); "
            f"por defecto {MOVEMENTS_QUERY_DEFAULT_LIMIT}"
        ),
    ),
    service: InventoryService = Depends(get_inventory_service),
) -> List[MovementResponse]:
    """Devuelve las entradas y salidas aplicadas, de la mas reciente a la mas antigua.

    El historial se conserva aunque el producto se elimine: cada asiento guarda
    el nombre que tenia el articulo en el momento del movimiento.
    """
    return to_movement_list(service.list_movements(product_id=product_id, limit=limit))


@router.get(
    "/low",
    response_model=List[ProductResponse],
    summary="Listar productos con stock bajo",
    responses={
        400: {"model": ErrorResponse, "description": "Umbral ausente o invalido"},
        503: {"model": ErrorResponse, "description": "Almacen no inicializado"},
    },
)
def list_low_stock(
    threshold: Optional[int] = Query(
        None, description=LOW_STOCK_QUERY_DESCRIPTION
    ),
    service: InventoryService = Depends(get_inventory_service),
) -> List[ProductResponse]:
    """Req 8.2-8.4: productos con Stock_Level menor o igual al umbral."""
    return to_response_list(service.list_low_stock_products(threshold))
