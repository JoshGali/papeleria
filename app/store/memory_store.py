"""In_Memory_Store: almacenamiento volatil de productos (Requerimiento 10).

La clase encapsula el estado para que la migracion futura a DynamoDB se
limite a proveer otra implementacion con la misma interfaz.
"""

import threading
from collections import deque
from typing import Callable, Deque, Dict, List, Optional

from app.core.config import MOVEMENTS_MAX_ENTRIES, STORE_MAX_PRODUCTS
from app.core.errors import (
    ConflictError,
    NotFoundError,
    StorageCapacityError,
    StoreNotReadyError,
)
from app.models.movement import StockMovement
from app.models.product import Product


class InMemoryStore:
    """Diccionario de productos protegido por un lock reentrante.

    El estado ``initialized`` distingue un almacen vacio pero operativo
    (Req 10.2, responde 200 con arreglo vacio) de uno que aun no arranca
    (Req 2.6, responde 503).
    """

    def __init__(
        self,
        capacity: int = STORE_MAX_PRODUCTS,
        movements_capacity: int = MOVEMENTS_MAX_ENTRIES,
    ) -> None:
        self._capacity = capacity
        self._products: Dict[str, Product] = {}
        # deque con tope: al llenarse descarta automaticamente los asientos
        # mas antiguos, evitando que el historial crezca sin limite.
        self._movements: Deque[StockMovement] = deque(maxlen=movements_capacity)
        self._initialized = False
        self._lock = threading.RLock()

    # -- Ciclo de vida ------------------------------------------------------
    def initialize(self) -> None:
        """Req 10.2 y 10.5: al arrancar el almacen queda vacio y disponible."""
        with self._lock:
            self._products.clear()
            self._movements.clear()
            self._initialized = True

    def shutdown(self) -> None:
        """Req 10.4: al detenerse se pierden todos los datos almacenados."""
        with self._lock:
            self._products.clear()
            self._movements.clear()
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        with self._lock:
            return self._initialized

    @property
    def capacity(self) -> int:
        return self._capacity

    def ensure_ready(self) -> None:
        """Req 2.6: bloquea cualquier operacion si el almacen no esta listo."""
        if not self.is_initialized:
            raise StoreNotReadyError(
                "El almacenamiento en memoria no esta inicializado todavia"
            )

    # -- Operaciones CRUD ---------------------------------------------------
    def count(self) -> int:
        with self._lock:
            return len(self._products)

    def is_full(self) -> bool:
        """Req 10.1 y 10.3: capacidad maxima de 10000 productos."""
        with self._lock:
            return len(self._products) >= self._capacity

    def add(self, product: Product) -> Product:
        """Inserta un producto nuevo respetando la capacidad del almacen."""
        with self._lock:
            self.ensure_ready()
            if product.product_id in self._products:
                raise ConflictError(
                    "Ya existe un producto registrado con ese Product_ID"
                )
            if len(self._products) >= self._capacity:
                # Req 10.3: se impide la insercion y se reporta 507.
                raise StorageCapacityError(
                    "Se excedio la capacidad de almacenamiento de "
                    f"{self._capacity} productos"
                )
            self._products[product.product_id] = product
            return product

    def get(self, product_id: str) -> Optional[Product]:
        with self._lock:
            self.ensure_ready()
            return self._products.get(product_id)

    def list_all(self) -> List[Product]:
        """Devuelve los productos en orden de insercion."""
        with self._lock:
            self.ensure_ready()
            return list(self._products.values())

    def mutate(
        self,
        product_id: str,
        mutator: Callable[[Product], Product],
        *,
        on_applied: Optional[Callable[[Product, Product], StockMovement]] = None,
    ) -> Product:
        """Aplica una modificacion de lectura-escritura de forma atomica.

        El lock se mantiene durante todo el ciclo leer-calcular-escribir, de
        modo que dos movimientos de stock simultaneos no puedan perder
        actualizaciones. Si ``mutator`` lanza una excepcion no se escribe nada,
        lo que respalda el rechazo total exigido por el Req 6.3. El Product_ID
        se conserva porque la clave del diccionario no cambia (Req 3.4).
        """
        with self._lock:
            self.ensure_ready()
            current = self._products.get(product_id)
            if current is None:
                raise NotFoundError(f"No existe un producto con el id {product_id}")
            updated = mutator(current)
            self._products[product_id] = updated
            if on_applied is not None:
                # Se ejecuta dentro del lock: el asiento del historial y el
                # cambio de stock quedan registrados en la misma seccion
                # critica, sin que otra operacion pueda colarse entre ambos.
                self._movements.append(on_applied(current, updated))
            return updated

    def delete(self, product_id: str) -> bool:
        """Req 4.1: elimina por completo el producto del almacen."""
        with self._lock:
            self.ensure_ready()
            return self._products.pop(product_id, None) is not None

    # -- Historial de movimientos -------------------------------------------
    def list_movements(
        self, product_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[StockMovement]:
        """Devuelve los movimientos del mas reciente al mas antiguo.

        El historial sobrevive a la eliminacion del producto: un asiento es un
        hecho ocurrido y cada uno guarda el nombre que tenia el articulo en ese
        momento.
        """
        with self._lock:
            self.ensure_ready()
            movements = [
                movement
                for movement in reversed(self._movements)
                if product_id is None or movement.product_id == product_id
            ]
            return movements[:limit] if limit is not None else movements

    def count_movements(self) -> int:
        with self._lock:
            return len(self._movements)

    def clear(self) -> None:
        """Vacia el almacen sin cambiar su estado de inicializacion."""
        with self._lock:
            self._products.clear()
            self._movements.clear()


#: Instancia compartida por la aplicacion.
store = InMemoryStore()
