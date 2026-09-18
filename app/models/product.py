"""Entidad de dominio Product.

Se mantiene independiente de Pydantic y de FastAPI para que la migracion
futura a DynamoDB (Req 10) solo tenga que reemplazar la capa de
almacenamiento.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from uuid import uuid4

from app.core.config import INITIAL_STOCK_LEVEL


def generate_product_id() -> str:
    """Genera un Product_ID unico (Req 1.2).

    Se usa UUID4 en su forma canonica: 36 caracteres alfanumericos con
    guiones, por lo que cumple tanto el maximo de 100 caracteres del Req 1.2
    como el formato mas estricto del Req 7.6 (<= 50 caracteres).
    """
    # UUID4 canonico: siempre 36 caracteres, dentro de ambos limites.
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Product:
    """Articulo del inventario."""

    name: str
    description: str
    price: Decimal
    product_id: str = field(default_factory=generate_product_id)
    stock: int = INITIAL_STOCK_LEVEL
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def copy_with(self, **changes: Any) -> "Product":
        """Devuelve una copia con los cambios aplicados y ``updated_at`` fresco.

        El Product_ID se conserva siempre (Req 3.4).
        """
        changes.pop("product_id", None)
        return replace(self, updated_at=_now(), **changes)

    def to_dict(self) -> Dict[str, Any]:
        """Representacion publica del producto (Req 2.7).

        Incluye las marcas de tiempo para que una interfaz pueda mostrar
        cuando se dio de alta y cuando se modifico por ultima vez.
        """
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),
            "stock": self.stock,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @property
    def is_visible(self) -> bool:
        """Req 2.1 y 2.3: solo es consultable con stock y precio distintos de cero."""
        return self.stock > 0 and self.price > 0
