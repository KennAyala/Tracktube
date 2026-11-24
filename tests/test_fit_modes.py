import pytest
from PIL import Image

from tracktube.core.fit_modes import FIT_MODES, build_filter_graph, render_preview


@pytest.mark.parametrize("mode", list(FIT_MODES))
def test_filtro_termina_en_v_y_fps(mode):
    graph = build_filter_graph(mode, 1920, 1080, 60)
    assert graph.endswith("fps=60[v]")
    assert "format=yuv420p" in graph


def test_modo_desconocido():
    with pytest.raises(ValueError):
        build_filter_graph("nada", 100, 100, 30)
    with pytest.raises(ValueError):
        render_preview(Image.new("RGB", (10, 10)), "nada", 100, 100)


@pytest.mark.parametrize("mode", list(FIT_MODES))
def test_preview_tiene_el_tamano_pedido(mode):
    image = Image.new("RGB", (300, 200), (255, 0, 0))
    assert render_preview(image, mode, 160, 90).size == (160, 90)
    assert render_preview(image, mode, 90, 160).size == (90, 160)


def test_ajustar_deja_barras_negras():
    image = Image.new("RGB", (100, 100), (255, 0, 0))
    result = render_preview(image, "ajustar", 200, 100)
    assert result.getpixel((5, 50)) == (0, 0, 0)
    assert result.getpixel((100, 50)) == (255, 0, 0)
