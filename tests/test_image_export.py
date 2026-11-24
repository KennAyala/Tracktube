from pathlib import Path

import pytest
from PIL import Image

from tracktube.core.image_export import (
    IMAGE_FILTERS, JPG_FILTER, PNG_FILTER, resolve_image_path, save_image,
)


def test_jpg_es_el_primer_filtro_y_por_tanto_el_defecto():
    assert IMAGE_FILTERS.split(";;") == [JPG_FILTER, PNG_FILTER]


@pytest.mark.parametrize("name", ["a.jpg", "a.JPG", "a.jpeg", "a.png", "a.PNG"])
def test_la_extension_escrita_manda(name):
    assert resolve_image_path(f"D:/fotos/{name}", PNG_FILTER if "jp" in name.lower() else JPG_FILTER) \
        == Path(f"D:/fotos/{name}")


def test_sin_extension_usa_el_filtro_elegido():
    assert resolve_image_path("D:/fotos/a", JPG_FILTER) == Path("D:/fotos/a.jpg")
    assert resolve_image_path("D:/fotos/a", PNG_FILTER) == Path("D:/fotos/a.png")


def test_sin_extension_ni_filtro_es_jpg():
    assert resolve_image_path("D:/fotos/a") == Path("D:/fotos/a.jpg")
    assert resolve_image_path("D:/fotos/a", "") == Path("D:/fotos/a.jpg")


def test_una_extension_no_valida_se_completa_con_el_filtro():
    assert resolve_image_path("D:/fotos/a.v2", PNG_FILTER) == Path("D:/fotos/a.v2.png")


def test_guarda_jpg_y_png(tmp_path):
    image = Image.new("RGB", (300, 200), (200, 40, 60))
    save_image(image, tmp_path / "a.jpg")
    save_image(image, tmp_path / "b.png")
    with Image.open(tmp_path / "a.jpg") as jpg, Image.open(tmp_path / "b.png") as png:
        assert jpg.format == "JPEG" and jpg.size == (300, 200)
        assert png.format == "PNG" and png.size == (300, 200)
        assert png.getpixel((10, 10)) == (200, 40, 60)


def test_guarda_siempre_en_rgb_aunque_la_imagen_tenga_alfa(tmp_path):
    image = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    save_image(image, tmp_path / "a.jpg")  # JPG no admite alfa
    save_image(image, tmp_path / "b.png")
    with Image.open(tmp_path / "a.jpg") as jpg, Image.open(tmp_path / "b.png") as png:
        assert jpg.mode == "RGB" and png.mode == "RGB"
