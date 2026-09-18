"""Entidad de dominio StockMovement: historial de movimientos de inventario.

Cada entrada o salida aplicada deja un asiento inmutable que registra cuanto
se movio y como quedo el Stock_Level. Es el equivalente a un kardex y permite
responder "que se vendio hoy" sin recalcular nada.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import uuid4

from app.models.product import Product


class MovementType(str, Enum):
    """Sentido del movimiento."""

    ENTRY = "entry"
    EXIT = "exit"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class StockMovement:
    """Asiento historico de un movimiento de stock ya aplicado.

    Es inmutable: un movimiento registrado no se corrige, se compensa con otro
    movimiento en sentido contrario.
    """

    product_id: str
    product_name: str
    type: MovementType
    quantity: int
    stock_before: int
    stock_after: int
    movement_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=_now)

    @classmethod
    def from_change(
        cls,
        *,
        before: Product,
        after: Product,
        movement_type: MovementType,
        quantity: int,
    ) -> "StockMovement":
        """Construye el asiento a partir del producto antes y despues del cambio.

        Se guarda el nombre vigente en ese momento para que el historial siga
        siendo legible aunque el producto se renombre o se elimine despues.
        """
        return cls(
            product_id=after.product_id,
            product_name=after.name,
            type=movement_type,
            quantity=quantity,
            stock_before=before.stock,
            stock_after=after.stock,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "movement_id": self.movement_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "type": self.type.value,
            "quantity": self.quantity,
            "stock_before": self.stock_before,
            "stock_after": self.stock_after,
            "created_at": self.created_at,
        }
