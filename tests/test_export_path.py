from pathlib import Path

from tracktube.config import BASE_DIR
from tracktube.core import export_path


def test_default_es_exports_uuid_mp4():
    first, second = export_path.new_default_path(), export_path.new_default_path()
    assert first.startswith("exports/") and first.endswith(".mp4")
    assert first != second


def test_resolve_relativa_a_la_app():
    assert export_path.resolve_path("exports/a.mp4") == BASE_DIR / "exports" / "a.mp4"


def test_resolve_agrega_extension():
    assert export_path.resolve_path("exports/a").suffix == ".mp4"


def test_change_folder_conserva_nombre():
    result = export_path.change_folder("exports/abc.mp4", "D:/musica")
    assert Path(result) == Path("D:/musica/abc.mp4")
