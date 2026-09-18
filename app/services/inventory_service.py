"""Reglas de negocio del Inventory_System.

La capa de servicio no conoce FastAPI: recibe datos ya validados por los
esquemas, aplica las reglas del inventario y lanza excepciones de dominio que
la capa HTTP traduce a respuestas.
"""

from typing import Any, Callable, Dict, List, Optional

from app.core.config import (
    LOW_STOCK_THRESHOLD_MAX,
    LOW_STOCK_THRESHOLD_MIN,
    MOVEMENTS_QUERY_DEFAULT_LIMIT,
    MOVEMENTS_QUERY_MAX_LIMIT,
    STOCK_CAPACITY_MAX,
)
from app.core.errors import NotFoundError, ValidationError
from app.models.movement import MovementType, StockMovement
from app.models.product import Product
from app.models.schemas import ProductCreate, ProductUpdate
from app.models.validators import validate_product_id
from app.store.memory_store import InMemoryStore

#: Campos que el cliente puede modificar mediante una actualizacion (Req 3.1).
UPDATABLE_FIELDS = ("name", "description", "price")


class InventoryService:
    """Operaciones de inventario sobre un almacen intercambiable."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    @property
    def store(self) -> InMemoryStore:
        """Almacen sobre el que opera el servicio."""
        return self._store

    # -- Requerimiento 1: crear --------------------------------------------
    def create_product(self, payload: ProductCreate) -> Product:
        """Crea un producto con Stock_Level inicial en cero (Req 1.1 y 1.6)."""
        self._store.ensure_ready()
        product = Product(
            name=payload.name,
            description=payload.description,
            price=payload.price,
        )
        # ``add`` aplica la capacidad maxima del almacen (Req 10.3 -> 507).
        return self._store.add(product)

    # -- Requerimiento 2: consultar ----------------------------------------
    def get_product(self, product_id: Any) -> Product:
        """Devuelve un producto consultable.

        Req 2.2: un Product_ID inexistente responde 404.
        Req 2.3: un producto con stock o precio en cero se filtra y tambien
        responde 404.
        """
        product = self._find(product_id)
        if product is None or not product.is_visible:
            raise NotFoundError(
                f"No existe un producto consultable con el id {product_id}"
            )
        return product

    def list_products(self, *, include_unavailable: bool = False) -> List[Product]:
        """Lista los productos del catalogo.

        Por defecto aplica el filtro del Req 2.4 y devuelve solo los productos
        con stock y precio distintos de cero. ``include_unavailable`` desactiva
        ese filtro para la vista de administracion, que necesita ver tambien
        los articulos agotados o sin precio asignado: de otro modo un producto
        recien creado (Stock_Level en cero) seria invisible hasta surtirlo.
        """
        products = self._store.list_all()
        if include_unavailable:
            return products
        return [p for p in products if p.is_visible]

    # -- Requerimiento 3: actualizar ---------------------------------------
    def update_product(self, product_id: Any, payload: ProductUpdate) -> Product:
        """Aplica solo los campos enviados cuyo valor realmente cambia."""
        changes = payload.provided_changes()
        if not changes:
            # Req 3.6: no se recibio ningun campo actualizable.
            raise ValidationError(
                "Debe enviar al menos un campo actualizable: "
                + ", ".join(UPDATABLE_FIELDS)
            )

        def apply(product: Product) -> Product:
            # Req 3.8: solo se tocan los campos cuyo valor difiere del actual.
            effective = {
                field: value
                for field, value in changes.items()
                if getattr(product, field) != value
            }
            if not effective:
                # Req 3.7: los valores enviados son identicos a los actuales.
                raise ValidationError(
                    "Los valores enviados son identicos a los actuales, "
                    "no hay cambios que aplicar"
                )
            # Req 3.4: copy_with preserva el Product_ID.
            # Req 3.5: el Stock_Level no es un campo actualizable.
            return product.copy_with(**effective)

        return self._mutate(product_id, apply)

    # -- Requerimiento 4: eliminar -----------------------------------------
    def delete_product(self, product_id: Any) -> None:
        """Req 4.1-4.3: elimina el producto o responde 404 si ya no existe."""
        valid_id = self._validate_id(product_id)
        self._store.ensure_ready()
        if not self._store.delete(valid_id):
            raise NotFoundError(
                f"No existe un producto con el id {valid_id} para eliminar"
            )

    # -- Requerimiento 5: entradas de stock --------------------------------
    def add_stock(self, product_id: Any, quantity: int) -> Product:
        """Incrementa el Stock_Level respetando la capacidad maxima."""

        def apply(product: Product) -> Product:
            new_level = product.stock + quantity
            if new_level > STOCK_CAPACITY_MAX:
                # Req 5.4: se excede la capacidad maxima de stock.
                raise ValidationError(
                    "Se excedio la capacidad maxima de stock de "
                    f"{STOCK_CAPACITY_MAX} unidades para este producto"
                )
            # Req 5.5: el nuevo nivel es el original mas la cantidad ingresada.
            return product.copy_with(stock=new_level)

        return self._mutate(
            product_id, apply, movement_type=MovementType.ENTRY, quantity=quantity
        )

    # -- Requerimiento 6: salidas de stock ---------------------------------
    def remove_stock(self, product_id: Any, quantity: int) -> Product:
        """Descuenta el Stock_Level solo si hay existencias suficientes."""

        def apply(product: Product) -> Product:
            if quantity > product.stock:
                # Req 6.3: se rechaza la operacion completa sin descontar nada.
                raise ValidationError(
                    "Stock insuficiente: se solicitaron "
                    f"{quantity} unidades y hay {product.stock} disponibles"
                )
            return product.copy_with(stock=product.stock - quantity)

        return self._mutate(
            product_id, apply, movement_type=MovementType.EXIT, quantity=quantity
        )

    # -- Requerimiento 8: disponibilidad -----------------------------------
    def list_available_products(self) -> List[Product]:
        """Req 8.1: productos con Stock_Level mayor a cero."""
        return [p for p in self._store.list_all() if p.stock > 0]

    def list_low_stock_products(self, threshold: Optional[Any]) -> List[Product]:
        """Req 8.2-8.4: productos con Stock_Level menor o igual al umbral."""
        valid_threshold = self._validate_threshold(threshold)
        return [p for p in self._store.list_all() if p.stock <= valid_threshold]

    # -- Utilidades internas ------------------------------------------------
    def _validate_id(self, product_id: Any) -> str:
        """Req 4.4 y 7.6: valida el formato antes de tocar el almacen."""
        try:
            return validate_product_id(product_id)
        except ValueError as exc:
            raise ValidationError(
                str(exc), errors=[_field_error("product_id", str(exc))]
            ) from exc

    def _validate_threshold(self, threshold: Optional[Any]) -> int:
        if threshold is None:
            # Req 8.3: el umbral es obligatorio.
            raise ValidationError(
                "Debe indicar el parametro 'threshold' para filtrar stock bajo",
                errors=[_field_error("threshold", "El umbral es obligatorio")],
            )
        if isinstance(threshold, bool) or not isinstance(threshold, int):
            raise ValidationError(
                "El umbral de stock bajo debe ser un numero entero",
                errors=[_field_error("threshold", "Debe ser un numero entero")],
            )
        if not LOW_STOCK_THRESHOLD_MIN <= threshold <= LOW_STOCK_THRESHOLD_MAX:
            # Req 8.4: fuera del rango permitido.
            message = (
                "El umbral debe estar entre "
                f"{LOW_STOCK_THRESHOLD_MIN} y {LOW_STOCK_THRESHOLD_MAX} unidades"
            )
            raise ValidationError(message, errors=[_field_error("threshold", message)])
        return threshold

    def _find(self, product_id: Any) -> Optional[Product]:
        valid_id = self._validate_id(product_id)
        self._store.ensure_ready()
        return self._store.get(valid_id)

    def _mutate(
        self,
        product_id: Any,
        mutator: Callable[[Product], Product],
        *,
        movement_type: Optional[MovementType] = None,
        quantity: int = 0,
    ) -> Product:
        """Ejecuta una modificacion atomica sobre un producto existente.

        No aplica el filtro de visibilidad del Req 2: las operaciones de
        escritura (Req 3, 5 y 6) deben alcanzar tambien a los productos recien
        creados, que aun tienen Stock_Level en cero.

        Cuando se indica ``movement_type`` se registra ademas el asiento del
        historial, dentro de la misma seccion critica que el cambio de stock.
        """
        valid_id = self._validate_id(product_id)
        self._store.ensure_ready()

        def record(before: Product, after: Product) -> StockMovement:
            assert movement_type is not None  # garantizado por el llamador
            return StockMovement.from_change(
                before=before,
                after=after,
                movement_type=movement_type,
                quantity=quantity,
            )

        # ``mutate`` lanza NotFoundError si el producto ya no existe.
        return self._store.mutate(
            valid_id, mutator, on_applied=record if movement_type else None
        )

    # -- Historial de movimientos ------------------------------------------
    def list_movements(
        self, product_id: Optional[Any] = None, limit: Optional[Any] = None
    ) -> List[StockMovement]:
        """Consulta el historial, del movimiento mas reciente al mas antiguo."""
        valid_id = self._validate_id(product_id) if product_id is not None else None
        valid_limit = self._validate_limit(limit)
        return self._store.list_movements(product_id=valid_id, limit=valid_limit)

    def _validate_limit(self, limit: Optional[Any]) -> int:
        if limit is None:
            return MOVEMENTS_QUERY_DEFAULT_LIMIT
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValidationError(
                "El parametro 'limit' debe ser un numero entero",
                errors=[_field_error("limit", "Debe ser un numero entero")],
            )
        if not 1 <= limit <= MOVEMENTS_QUERY_MAX_LIMIT:
            message = (
                "El parametro 'limit' debe estar entre 1 y "
                f"{MOVEMENTS_QUERY_MAX_LIMIT} movimientos"
            )
            raise ValidationError(message, errors=[_field_error("limit", message)])
        return limit


def _field_error(field: str, message: str) -> Dict[str, str]:
    return {"field": field, "message": message, "type": "value_error"}
