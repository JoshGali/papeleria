"""In_Memory_Store: almacenamiento volatil de productos (Requerimiento 10).

La clase encapsula el estado para que la migracion futura a DynamoDB se
limite a proveer otra implementacion con la misma interfaz.
"""

import threading
from typing import Callable, Dict, List, Optional

from app.core.config import STORE_MAX_PRODUCTS
from app.core.errors import (
    ConflictError,
    NotFoundError,
    StorageCapacityError,
    StoreNotReadyError,
)
from app.models.product import Product


class InMemoryStore:
    """Diccionario de productos protegido por un lock reentrante.

    El estado ``initialized`` distingue un almacen vacio pero operativo
    (Req 10.2, responde 200 con arreglo vacio) de uno que aun no arranca
    (Req 2.6, responde 503).
    """

    def __init__(self, capacity: int = STORE_MAX_PRODUCTS) -> None:
        self._capacity = capacity
        self._products: Dict[str, Product] = {}
        self._initialized = False
        self._lock = threading.RLock()

    # -- Ciclo de vida ------------------------------------------------------
    def initialize(self) -> None:
        """Req 10.2 y 10.5: al arrancar el almacen queda vacio y disponible."""
        with self._lock:
            self._products.clear()
            self._initialized = True

    def shutdown(self) -> None:
        """Req 10.4: al detenerse se pierden todos los datos almacenados."""
        with self._lock:
            self._products.clear()
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
        self, product_id: str, mutator: Callable[[Product], Product]
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
            return updated

    def delete(self, product_id: str) -> bool:
        """Req 4.1: elimina por completo el producto del almacen."""
        with self._lock:
            self.ensure_ready()
            return self._products.pop(product_id, None) is not None

    def clear(self) -> None:
        """Vacia el almacen sin cambiar su estado de inicializacion."""
        with self._lock:
            self._products.clear()


#: Instancia compartida por la aplicacion.
store = InMemoryStore()
