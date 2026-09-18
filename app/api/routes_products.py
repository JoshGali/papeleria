"""Endpoints del catalogo de productos (Requerimientos 1, 2, 3 y 4)."""

from typing import List

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.api.dependencies import get_inventory_service
from app.models.schemas import (
    ErrorResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    to_response_list,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/products", tags=["Productos"])

_PRODUCT_ID_PATH = Path(
    ...,
    description="Identificador del producto (alfanumerico y guiones, max 50)",
)

_COMMON_ERRORS = {
    400: {"model": ErrorResponse, "description": "Datos de entrada invalidos"},
    404: {"model": ErrorResponse, "description": "Producto no encontrado"},
}


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un producto",
    responses={
        400: {"model": ErrorResponse, "description": "Datos de entrada invalidos"},
        507: {"model": ErrorResponse, "description": "Capacidad de almacen excedida"},
    },
)
def create_product(
    payload: ProductCreate,
    service: InventoryService = Depends(get_inventory_service),
) -> ProductResponse:
    """Req 1.1: registra el producto con Stock_Level en cero y responde 201."""
    product = service.create_product(payload)
    return ProductResponse.from_product(product)


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="Listar productos disponibles para consulta",
    responses={
        503: {"model": ErrorResponse, "description": "Almacen no inicializado"},
    },
)
def list_products(
    include_unavailable: bool = Query(
        False,
        description=(
            "Vista de administracion: incluye tambien los productos agotados "
            "o sin precio asignado, que el filtro por defecto oculta"
        ),
    ),
    service: InventoryService = Depends(get_inventory_service),
) -> List[ProductResponse]:
    """Req 2.4-2.6: lista los productos con stock y precio distintos de cero.

    Con el almacen vacio devuelve un arreglo vacio (Req 2.5); si el almacen no
    esta inicializado responde 503 (Req 2.6).

    ``include_unavailable=true`` levanta el filtro del Req 2.4 para la pantalla
    de administracion. El comportamiento por defecto no cambia.
    """
    return to_response_list(
        service.list_products(include_unavailable=include_unavailable)
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Consultar un producto por su identificador",
    responses=_COMMON_ERRORS,
)
def get_product(
    product_id: str = _PRODUCT_ID_PATH,
    service: InventoryService = Depends(get_inventory_service),
) -> ProductResponse:
    """Req 2.1-2.3: devuelve el producto o 404 si no existe o esta filtrado."""
    return ProductResponse.from_product(service.get_product(product_id))


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Actualizar campos de un producto",
    responses=_COMMON_ERRORS,
)
def update_product(
    payload: ProductUpdate,
    product_id: str = _PRODUCT_ID_PATH,
    service: InventoryService = Depends(get_inventory_service),
) -> ProductResponse:
    """Req 3: actualiza solo los campos enviados cuyo valor realmente cambia."""
    return ProductResponse.from_product(service.update_product(product_id, payload))


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Actualizar campos de un producto (alias de PATCH)",
    responses=_COMMON_ERRORS,
)
def replace_product(
    payload: ProductUpdate,
    product_id: str = _PRODUCT_ID_PATH,
    service: InventoryService = Depends(get_inventory_service),
) -> ProductResponse:
    """Alias de ``PATCH`` con identica semantica parcial (Req 3.8)."""
    return ProductResponse.from_product(service.update_product(product_id, payload))


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un producto",
    responses=_COMMON_ERRORS,
)
def delete_product(
    product_id: str = _PRODUCT_ID_PATH,
    service: InventoryService = Depends(get_inventory_service),
) -> Response:
    """Req 4.1-4.5: elimina el producto y responde 204 sin cuerpo."""
    service.delete_product(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
