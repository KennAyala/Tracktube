from PIL import Image

from tracktube.core.media_info import has_transparency


def test_detecta_canal_alfa():
    assert has_transparency(Image.new("RGBA", (4, 4), (255, 255, 255, 0)))
    assert has_transparency(Image.new("LA", (4, 4)))


def test_imagen_opaca_no_tiene_transparencia():
    assert not has_transparency(Image.new("RGB", (4, 4)))
    assert not has_transparency(Image.new("L", (4, 4)))


def test_detecta_transparencia_indexada_de_png(tmp_path):
    path = tmp_path / "indexed.png"
    image = Image.new("P", (4, 4), 0)
    image.putpalette([255, 255, 255] * 256)
    image.save(path, transparency=0)
    with Image.open(path) as saved:
        assert has_transparency(saved)
