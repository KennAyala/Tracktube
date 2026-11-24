from pathlib import Path

from tracktube.config import BASE_DIR
from tracktube.core import export_path


def test_nombre_por_defecto_es_uuid_mp4():
    first, second = export_path.new_default_filename(), export_path.new_default_filename()
    assert first.endswith(".mp4") and "/" not in first
    assert first != second


def test_resolve_relativa_a_la_app():
    assert export_path.resolve_path("exports/a.mp4") == BASE_DIR / "exports" / "a.mp4"


def test_resolve_agrega_extension():
    assert export_path.resolve_path("exports/a").suffix == ".mp4"


def test_build_une_carpeta_y_nombre():
    assert export_path.build_path("exports", "a.mp4") == BASE_DIR / "exports" / "a.mp4"
    assert export_path.build_path("D:/musica", "a.mp4") == Path("D:/musica/a.mp4")
    assert export_path.build_path(" D:/musica ", " a.mp4 ") == Path("D:/musica/a.mp4")


def test_build_agrega_la_extension_si_falta():
    assert export_path.build_path("D:/musica", "sin-extension") == Path("D:/musica/sin-extension.mp4")
