import pytest
from PIL import Image

from tracktube.core.fit_modes import (
    BACKGROUNDS, FIT_MODES, build_filter_graph, render_preview,
)


@pytest.mark.parametrize("mode", FIT_MODES)
def test_filtro_termina_en_v_y_fps(mode):
    graph = build_filter_graph(mode, 1920, 1080, 60)
    assert graph.endswith("fps=60[v]")
    assert "format=yuv420p" in graph


@pytest.mark.parametrize("background", BACKGROUNDS)
@pytest.mark.parametrize("shadow", [False, True])
def test_filtro_con_fondo_sombra_y_margen(background, shadow):
    graph = build_filter_graph("ajustar", 1920, 1080, 30, background, shadow, 10)
    assert graph.endswith("fps=30[v]")
    assert ("[shadow]" in graph) == shadow
    assert ("[2:v]" in graph) == (background == "personalizado")
    assert ("gblur" in graph) == (background == "desenfocado" or shadow)


def test_margen_reduce_el_album_art():
    # 10% de 1080 = 108 px por lado
    graph = build_filter_graph("ajustar", 1920, 1080, 30, margin=10)
    assert "scale=1704:864" in graph


def test_sin_extras_usa_el_filtro_simple():
    assert "pad=" in build_filter_graph("ajustar", 1920, 1080, 30)


def test_fondo_y_sombra_se_ignoran_fuera_de_ajustar():
    simple = build_filter_graph("cortar", 1920, 1080, 30)
    assert build_filter_graph("cortar", 1920, 1080, 30, "desenfocado", True, 20) == simple


def test_modo_y_fondo_desconocidos():
    with pytest.raises(ValueError):
        build_filter_graph("nada", 100, 100, 30)
    with pytest.raises(ValueError):
        build_filter_graph("ajustar", 100, 100, 30, "nada")
    with pytest.raises(ValueError):
        render_preview(Image.new("RGB", (10, 10)), "nada", 100, 100)
    with pytest.raises(ValueError):
        render_preview(Image.new("RGB", (10, 10)), "ajustar", 100, 100, "nada")


@pytest.mark.parametrize("mode", FIT_MODES)
def test_preview_tiene_el_tamano_pedido(mode):
    image = Image.new("RGB", (300, 200), (255, 0, 0))
    assert render_preview(image, mode, 160, 90).size == (160, 90)
    assert render_preview(image, mode, 90, 160).size == (90, 160)


@pytest.mark.parametrize("background", BACKGROUNDS)
def test_preview_con_fondo_sombra_y_margen(background):
    image = Image.new("RGB", (300, 200), (255, 0, 0))
    custom = Image.new("RGB", (50, 50), (0, 0, 255))
    result = render_preview(image, "ajustar", 160, 90, background, True, 15, custom)
    assert result.size == (160, 90)


def test_ajustar_deja_barras_negras():
    image = Image.new("RGB", (100, 100), (255, 0, 0))
    result = render_preview(image, "ajustar", 200, 100)
    assert result.getpixel((5, 50)) == (0, 0, 0)
    assert result.getpixel((100, 50)) == (255, 0, 0)


def test_margen_aleja_el_album_art_del_borde():
    image = Image.new("RGB", (100, 100), (255, 0, 0))
    sin_margen = render_preview(image, "ajustar", 100, 100)
    con_margen = render_preview(image, "ajustar", 100, 100, margin=20)
    assert sin_margen.getpixel((5, 5)) == (255, 0, 0)
    assert con_margen.getpixel((5, 5)) == (0, 0, 0)
    assert con_margen.getpixel((50, 50)) == (255, 0, 0)


def test_fondo_personalizado_se_ve_en_el_preview():
    image = Image.new("RGB", (100, 100), (255, 0, 0))
    custom = Image.new("RGB", (100, 100), (0, 0, 255))
    result = render_preview(image, "ajustar", 200, 100, "personalizado", False, 0, custom)
    assert result.getpixel((5, 50)) == (0, 0, 255)


def test_sombra_oscurece_junto_al_album_art():
    image = Image.new("RGB", (100, 100), (255, 255, 255))
    custom = Image.new("RGB", (100, 100), (255, 255, 255))
    result = render_preview(image, "ajustar", 400, 400, "personalizado", True, 20, custom)
    assert result.getpixel((200, 200)) == (255, 255, 255)
    # Justo debajo del album art (con margen 20% termina en y=320) hay sombra
    assert sum(result.getpixel((200, 325))) < 3 * 255
