"""Constantes y limites de negocio del Gestor de Inventario.

Cada constante referencia el criterio de aceptacion del documento de
requerimientos (docs/requirements.md) que la origina.
"""

from decimal import Decimal
from typing import Final

# --- Identificadores -------------------------------------------------------
# Req 1.2: el Product_ID generado tiene como maximo 100 caracteres.
PRODUCT_ID_GENERATED_MAX_LENGTH: Final[int] = 100
# Req 7.6: un Product_ID recibido debe ser alfanumerico/guiones y <= 50 chars.
PRODUCT_ID_MAX_LENGTH: Final[int] = 50
PRODUCT_ID_PATTERN: Final[str] = r"^[A-Za-z0-9-]+$"

# --- Producto --------------------------------------------------------------
# Req 1.4 / Req 7.2: nombre no vacio y de maximo 200 caracteres.
NAME_MAX_LENGTH: Final[int] = 200
# Req 1.5: en la creacion la descripcion no puede superar 500 caracteres.
DESCRIPTION_CREATE_MAX_LENGTH: Final[int] = 500
# Req 7.3: regla general de validacion de descripcion (aplica a updates).
DESCRIPTION_MAX_LENGTH: Final[int] = 1000

# Req 7.4: precio no negativo, <= 999999999.99 y con maximo 2 decimales.
PRICE_MIN: Final[Decimal] = Decimal("0")
PRICE_MAX: Final[Decimal] = Decimal("999999999.99")
PRICE_MAX_DECIMAL_PLACES: Final[int] = 2

# Req 1.6: todo producto nuevo inicia con Stock_Level en cero.
INITIAL_STOCK_LEVEL: Final[int] = 0

# --- Stock -----------------------------------------------------------------
# Req 7.5: cantidad de stock no negativa y <= 2147483647.
STOCK_LEVEL_MIN: Final[int] = 0
STOCK_LEVEL_MAX: Final[int] = 2147483647

# Req 5.1 / 5.3: cantidad de una entrada entre 1 y 999999.
STOCK_ENTRY_QUANTITY_MIN: Final[int] = 1
STOCK_ENTRY_QUANTITY_MAX: Final[int] = 999999
# Req 5.4: el Stock_Level resultante de una entrada no puede superar 999999.
STOCK_CAPACITY_MAX: Final[int] = 999999

# Req 6.1 / 6.4: cantidad de una salida entre 1 y 999999999.
STOCK_EXIT_QUANTITY_MIN: Final[int] = 1
STOCK_EXIT_QUANTITY_MAX: Final[int] = 999999999

# --- Consultas de disponibilidad ------------------------------------------
# Req 8.2 / 8.4: umbral de stock bajo entre 1 y 10000 unidades.
LOW_STOCK_THRESHOLD_MIN: Final[int] = 1
LOW_STOCK_THRESHOLD_MAX: Final[int] = 10000

# --- Almacenamiento en memoria --------------------------------------------
# Req 10.1 / 10.3: capacidad maxima del In_Memory_Store.
STORE_MAX_PRODUCTS: Final[int] = 10000

# --- Historial de movimientos ---------------------------------------------
#: Asientos conservados en memoria. Al llenarse se descartan los mas antiguos,
#: de modo que el historial no crezca sin limite durante la ejecucion.
MOVEMENTS_MAX_ENTRIES: Final[int] = 50000
#: Tope del parametro 'limit' al consultar el historial.
MOVEMENTS_QUERY_MAX_LIMIT: Final[int] = 1000
MOVEMENTS_QUERY_DEFAULT_LIMIT: Final[int] = 100

# --- Errores y tiempos -----------------------------------------------------
# Req 9.1-9.3: el mensaje de error debe medir entre 10 y 200 caracteres.
ERROR_MESSAGE_MIN_LENGTH: Final[int] = 10
ERROR_MESSAGE_MAX_LENGTH: Final[int] = 200
# Req 9.6: una peticion que supere 30 segundos termina en 504.
REQUEST_TIMEOUT_SECONDS: Final[float] = 30.0

#: Texto de ayuda del parametro 'threshold' en la documentacion OpenAPI.
LOW_STOCK_QUERY_DESCRIPTION: Final[str] = (
    "Umbral de unidades, obligatorio, entre "
    f"{LOW_STOCK_THRESHOLD_MIN} y {LOW_STOCK_THRESHOLD_MAX}"
)

API_TITLE: Final[str] = "Gestor de Inventario - Papeleria"
API_VERSION: Final[str] = "1.0.0"
