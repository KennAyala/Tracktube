import xml.etree.ElementTree as ET

from PySide6.QtGui import QIcon

from tracktube.config import BASE_DIR, ICON_PATH

SVG_PATH = BASE_DIR / "assets" / "logo.svg"
SVG_NS = "{http://www.w3.org/2000/svg}"


def test_el_logo_svg_es_valido():
    root = ET.parse(SVG_PATH).getroot()
    assert root.tag == f"{SVG_NS}svg"
    assert root.get("viewBox") == "0 0 1254 1254"
    # fondo, T blanca y triángulo rojo
    fills = [path.get("fill") for path in root.iter(f"{SVG_NS}path")]
    assert fills == ["#0a0a0a", "#ffffff", "#fc0818"]


def test_el_icono_de_la_app_existe_y_carga(qapp):
    assert ICON_PATH.is_file()
    icon = QIcon(str(ICON_PATH))
    assert not icon.isNull()
    assert not icon.pixmap(32, 32).isNull()


def test_el_readme_usa_el_logo():
    assert "assets/logo.svg" in (BASE_DIR / "README.md").read_text(encoding="utf-8")
