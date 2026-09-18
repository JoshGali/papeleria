# Gestor de Inventario - Papeleria

API REST construida con **FastAPI** para administrar el inventario de una
papeleria: alta de productos, consulta, actualizacion, baja, entradas y
salidas de stock y reportes de disponibilidad.

La persistencia es **en memoria** (Requerimiento 10) y esta encapsulada tras
una interfaz propia para que la migracion futura a DynamoDB solo tenga que
sustituir esa capa.

## Puesta en marcha

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

- API: <http://127.0.0.1:8000>
- Documentacion interactiva (Swagger): <http://127.0.0.1:8000/docs>
- Esquema OpenAPI: <http://127.0.0.1:8000/openapi.json>

## Pruebas

```bash
pytest            # 173 pruebas
pytest -v         # detalle por criterio de aceptacion
```

La suite esta organizada por requerimiento (`tests/test_req01_create.py`,
`tests/test_req02_query.py`, ...), mas pruebas de concurrencia, pruebas
asincronas de extremo a extremo y pruebas basadas en propiedades con
Hypothesis.

## Endpoints

| Metodo | Ruta | Descripcion | Req |
|---|---|---|---|
| `POST` | `/products` | Crea un producto (stock inicial 0) | 1 |
| `GET` | `/products` | Lista los productos consultables | 2 |
| `GET` | `/products/{product_id}` | Consulta un producto | 2 |
| `PATCH` / `PUT` | `/products/{product_id}` | Actualiza nombre, descripcion o precio | 3 |
| `DELETE` | `/products/{product_id}` | Elimina un producto | 4 |
| `POST` | `/stock/entries` | Registra una entrada de stock | 5 |
| `POST` | `/stock/exits` | Registra una salida de stock | 6 |
| `GET` | `/stock/available` | Productos con stock mayor a cero | 8 |
| `GET` | `/stock/low?threshold=N` | Productos con stock menor o igual a N | 8 |
| `GET` | `/health` | Estado del sistema y del almacen | - |

### Ejemplos

```bash
# Crear un producto
curl -X POST http://127.0.0.1:8000/products \
  -H 'content-type: application/json' \
  -d '{"name":"Tijeras escolares","description":"Punta roma de 5 pulgadas","price":32.50}'

# Registrar una entrada de 40 unidades
curl -X POST http://127.0.0.1:8000/stock/entries \
  -H 'content-type: application/json' \
  -d '{"product_id":"<id>","quantity":40}'

# Registrar la venta de 3 unidades
curl -X POST http://127.0.0.1:8000/stock/exits \
  -H 'content-type: application/json' \
  -d '{"product_id":"<id>","quantity":3}'

# Productos por debajo de 10 unidades
curl 'http://127.0.0.1:8000/stock/low?threshold=10'
```

### Formato de producto

```json
{
  "product_id": "784181ef-03a9-4f72-a72b-ff535580dbe1",
  "name": "Tijeras escolares",
  "description": "Punta roma de 5 pulgadas",
  "price": 32.5,
  "stock": 40
}
```

### Formato de error (Requerimiento 9)

```json
{
  "error_type": "validation_error",
  "message": "Se encontraron 2 errores de validacion en los campos: name, price",
  "status_code": 400,
  "errors": [
    {"field": "name", "message": "El nombre no puede estar vacio", "type": "value_error"},
    {"field": "price", "message": "El precio no puede ser negativo", "type": "value_error"}
  ]
}
```

`error_type` toma uno de estos valores: `validation_error` (400), `not_found`
(404), `method_not_allowed` (405), `conflict` (409), `internal_error` (500),
`service_unavailable` (503), `timeout` (504) y `storage_capacity_exceeded`
(507). El campo `errors` aparece cuando hay errores de campo que detallar.

## Reglas de validacion

| Campo | Regla | Req |
|---|---|---|
| `name` | String no vacio, maximo 200 caracteres | 1.4, 7.2, 7.7 |
| `description` | String no vacio; maximo 500 al crear y 1000 al actualizar | 1.5, 7.3, 7.8 |
| `price` | Numerico, de 0 a 999999999.99, maximo 2 decimales | 7.4, 7.9 |
| `product_id` | String alfanumerico con guiones, de 1 a 50 caracteres | 7.6, 7.11 |
| `quantity` (entrada) | Entero de 1 a 999999; el stock resultante no supera 999999 | 5.1, 5.3, 5.4 |
| `quantity` (salida) | Entero de 1 a 999999999, nunca mayor al stock actual | 6.1, 6.3, 6.4 |
| `threshold` | Entero obligatorio de 1 a 10000 | 8.2, 8.3, 8.4 |

## Estructura del proyecto

```
app/
  main.py                      Creacion de la app, ciclo de vida y /health
  api/
    dependencies.py            Inyeccion del almacen y del servicio
    routes_products.py         Endpoints de catalogo (Req 1, 2, 3, 4)
    routes_stock.py            Endpoints de stock (Req 5, 6, 8)
  core/
    config.py                  Limites de negocio, uno por criterio
    errors.py                  Excepciones de dominio y formato de error
    handlers.py                Manejadores globales de excepciones
    logging.py                 Bitacora con timestamp, ruta y metodo
    middleware.py              Timeout de 30 s y red de seguridad de errores
  models/
    product.py                 Entidad de dominio
    schemas.py                 Esquemas de entrada y salida
    validators.py              Reglas del Requerimiento 7
  services/
    inventory_service.py       Reglas de negocio del inventario
  store/
    memory_store.py            In_Memory_Store con capacidad y lock
tests/                         Una suite por requerimiento
docs/requirements.md           Documento de requerimientos de origen
```

Las capas estan separadas a proposito: los endpoints solo traducen HTTP, el
servicio concentra las reglas y el almacen guarda los datos. Migrar a DynamoDB
significa escribir una clase con la misma interfaz que `InMemoryStore` y
cambiar la dependencia `get_store`.

## Decisiones de diseno

Estos puntos resuelven ambiguedades o tensiones del documento de
requerimientos; se dejan explicitos para que puedan revisarse.

1. **Limite de la descripcion.** El Req 1.5 fija 500 caracteres en la creacion
   y el Req 7.3 fija 1000 como regla general. Se aplica el limite estricto de
   500 al crear y el de 1000 al actualizar, que es la lectura que satisface
   ambos criterios a la vez.

2. **Longitud del `product_id`.** El Req 1.2 permite hasta 100 caracteres y el
   Req 7.6 rechaza cualquier identificador de mas de 50. El sistema genera
   UUID4 (36 caracteres alfanumericos con guiones), que cumple los dos.

3. **Productos filtrados y operaciones de escritura.** El filtro de "stock y
   precio distintos de cero" del Req 2.3 se aplica solo a las consultas del
   Req 2. Las operaciones de actualizacion, eliminacion y movimientos de stock
   si alcanzan a esos productos: de lo contrario un producto recien creado
   (stock 0) seria imposible de surtir. Como consecuencia, un producto nuevo
   no aparece en `GET /products` hasta que recibe su primera entrada de stock;
   mientras tanto puede verse en `GET /stock/low`.

4. **Valores significativos.** El Req 1.3 pide validar que los campos
   presentes tengan valores significativos, por lo que un `name` o una
   `description` en blanco se rechazan con 400.

5. **`stock` no es actualizable.** Los esquemas prohiben campos extra, asi que
   enviar `stock` en una actualizacion devuelve 400 (Req 3.5). El stock solo
   cambia mediante entradas y salidas.

6. **Atomicidad de los movimientos.** FastAPI ejecuta los endpoints sincronos
   en un pool de hilos, de modo que dos salidas simultaneas del mismo producto
   compiten de verdad. El ciclo leer-calcular-escribir se realiza dentro del
   lock del almacen (`InMemoryStore.mutate`), lo que evita actualizaciones
   perdidas y respalda el rechazo total del Req 6.3. Hay pruebas dedicadas en
   `tests/test_concurrency.py`.

7. **400 en lugar de 422.** FastAPI responde 422 ante errores de validacion;
   los requerimientos exigen 400, por lo que un manejador global convierte
   todo `RequestValidationError` al formato del Req 9 con codigo 400.

## Limitaciones conocidas

- Los datos viven solo en memoria: al detener el proceso se pierde todo
  (Req 10.4) y al reiniciar el almacen arranca vacio (Req 10.5).
- El estado no se comparte entre varios procesos de uvicorn; con `--workers N`
  cada proceso tendria su propio inventario. Es una consecuencia esperada de
  la fase en memoria y desaparece con DynamoDB.
- La API no incluye autenticacion ni autorizacion; no estan en el alcance de
  este documento de requerimientos.
