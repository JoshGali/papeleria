"""La interfaz web servida por la propia aplicacion.

No prueban el comportamiento del navegador, sino que los archivos se sirven y
que siguen existiendo los endpoints de los que depende la pantalla: si alguno
se renombra, estas pruebas fallan antes de que la interfaz se rompa en vivo.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import STATIC_DIR

#: Rutas que app.js consume. Cambiar una sin actualizar la interfaz la rompe.
RUTAS_USADAS_POR_LA_INTERFAZ = [
    ("GET", "/health"),
    ("GET", "/products?include_unavailable=true"),
    ("GET", "/stock/movements?limit=500"),
]


def test_la_raiz_entrega_la_pantalla(client: TestClient) -> None:
    """La interfaz vive en la raiz del servidor."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>Inventario - Papeleria</title>" in response.text


@pytest.mark.parametrize("archivo", ["styles.css", "app.js"])
def test_los_recursos_estaticos_se_sirven(client: TestClient, archivo: str) -> None:
    """La hoja de estilos y el script se entregan desde /static."""
    response = client.get(f"/static/{archivo}")

    assert response.status_code == 200
    assert response.content


def test_la_carpeta_estatica_se_resuelve_desde_el_paquete() -> None:
    """La ruta no depende del directorio desde el que se lance uvicorn."""
    assert STATIC_DIR.is_dir()
    assert (STATIC_DIR / "index.html").is_file()


@pytest.mark.parametrize("metodo,ruta", RUTAS_USADAS_POR_LA_INTERFAZ)
def test_los_endpoints_que_usa_la_interfaz_responden(
    client: TestClient, metodo: str, ruta: str
) -> None:
    """Contrato entre la interfaz y la API: estas rutas deben seguir vivas."""
    response = client.request(metodo, ruta)

    assert response.status_code == 200, f"{metodo} {ruta} -> {response.status_code}"


def test_la_interfaz_no_referencia_recursos_externos() -> None:
    """Todo se sirve en local: la papeleria debe funcionar sin internet."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    externos = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)

    assert externos == []


def test_la_documentacion_sigue_disponible(client: TestClient) -> None:
    """Montar la interfaz en la raiz no debe tapar Swagger."""
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_una_ruta_desconocida_no_devuelve_la_pantalla(client: TestClient) -> None:
    """La interfaz no se sirve como comodin: un 404 sigue siendo JSON."""
    response = client.get("/ruta/inexistente")

    assert response.status_code == 404
    assert response.json()["error_type"] == "not_found"


def test_el_script_declara_el_parametro_de_administracion() -> None:
    """La tabla debe pedir tambien los agotados (Req 2.3 filtra el listado)."""
    script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "include_unavailable=true" in script
