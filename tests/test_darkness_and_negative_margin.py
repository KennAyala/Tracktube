"""Oscuridad del fondo y margen negativo: filtro de FFmpeg, preview y exportación real."""
import subprocess

import pytest
from PIL import Image

from audio_helpers import make_wav
from tracktube.core.exporter import export_video, get_ffmpeg_exe
from tracktube.core.fit_modes import (
    MAX_DARKNESS, MAX_MARGIN, MIN_MARGIN, build_filter_graph, render_preview,
)


def red():
    return Image.new("RGB", (100, 100), (255, 0, 0))


def white():
    return Image.new("RGB", (100, 100), (255, 255, 255))


# --- Oscuridad del fondo: filtro ---------------------------------------------------


@pytest.mark.parametrize("background", ["desenfocado", "personalizado"])
def test_la_oscuridad_se_aplica_solo_al_fondo(background):
    graph = build_filter_graph("ajustar", 1920, 1080, 30, background, darkness=40)
    # 40% más oscuro = el color se multiplica por 0.6, justo antes de etiquetar el fondo
    assert "colorchannelmixer=rr=0.6:gg=0.6:bb=0.6[bg]" in graph


@pytest.mark.parametrize("background", ["desenfocado", "personalizado"])
def test_sin_oscuridad_no_se_agrega_ningun_filtro(background):
    assert "colorchannelmixer" not in build_filter_graph("ajustar", 1920, 1080, 30, background)


def test_oscuridad_maxima_vuelve_negro_el_fondo():
    graph = build_filter_graph("ajustar", 1920, 1080, 30, "personalizado", darkness=100)
    assert "colorchannelmixer=rr=0:gg=0:bb=0[bg]" in graph


def test_la_oscuridad_no_afecta_sin_fondo_ni_fuera_de_ajustar():
    sin_fondo = build_filter_graph("ajustar", 1920, 1080, 30, "ninguno", margin=10)
    assert build_filter_graph("ajustar", 1920, 1080, 30, "ninguno", margin=10, darkness=60) \
        == sin_fondo
    for mode in ("cortar", "estirar"):
        assert build_filter_graph(mode, 1920, 1080, 30, "desenfocado", darkness=60) \
            == build_filter_graph(mode, 1920, 1080, 30)


def test_la_oscuridad_no_oscurece_la_sombra_ni_el_album_art():
    graph = build_filter_graph("ajustar", 1920, 1080, 30, "personalizado", True, 10, darkness=50)
    assert graph.count("rr=0.5:gg=0.5:bb=0.5") == 1  # solo el fondo
    assert "[shadow]" in graph


# --- Oscuridad del fondo: preview ---------------------------------------------------


def test_la_oscuridad_oscurece_el_fondo_en_el_preview():
    base = render_preview(red(), "ajustar", 200, 100, "personalizado", background_image=white())
    medio = render_preview(red(), "ajustar", 200, 100, "personalizado",
                           background_image=white(), darkness=50)
    negro = render_preview(red(), "ajustar", 200, 100, "personalizado",
                           background_image=white(), darkness=100)
    assert base.getpixel((5, 50)) == (255, 255, 255)
    assert all(abs(channel - 128) <= 1 for channel in medio.getpixel((5, 50)))
    assert negro.getpixel((5, 50)) == (0, 0, 0)


def test_la_oscuridad_no_toca_el_album_art_en_el_preview():
    result = render_preview(red(), "ajustar", 200, 100, "personalizado",
                            background_image=white(), darkness=100)
    assert result.getpixel((100, 50)) == (255, 0, 0)


def test_la_oscuridad_oscurece_el_fondo_desenfocado():
    image = Image.new("RGB", (100, 100), (200, 200, 200))
    plain = render_preview(image, "ajustar", 200, 100, "desenfocado")
    dark = render_preview(image, "ajustar", 200, 100, "desenfocado", darkness=75)
    assert dark.getpixel((5, 50))[0] < plain.getpixel((5, 50))[0] * 0.4


def test_la_oscuridad_se_ignora_sin_fondo_y_fuera_de_ajustar():
    assert render_preview(red(), "ajustar", 200, 100, darkness=80).getpixel((5, 50)) == (0, 0, 0)
    assert render_preview(red(), "cortar", 200, 100, "desenfocado", darkness=80).tobytes() \
        == render_preview(red(), "cortar", 200, 100).tobytes()


def test_el_rango_de_oscuridad():
    assert MAX_DARKNESS == 100


# --- Margen negativo ------------------------------------------------------------------


def test_el_margen_acepta_valores_negativos():
    assert MIN_MARGIN < 0 < MAX_MARGIN


def test_un_margen_negativo_agranda_el_album_art_en_el_filtro():
    # -10% de 1080 = -108 px por lado: la caja pasa de 1920x1080 a 2136x1296
    graph = build_filter_graph("ajustar", 1920, 1080, 30, margin=-10)
    assert "scale=2136:1296" in graph
    assert "pad=" not in graph  # ya no usa el filtro simple


def test_un_margen_negativo_agranda_el_album_art_en_el_preview():
    cuadrada = red()  # 100x100 en un cuadro de 200x100
    sin_margen = render_preview(cuadrada, "ajustar", 200, 100)
    con_margen = render_preview(cuadrada, "ajustar", 200, 100, margin=-50)
    assert sin_margen.getpixel((5, 50)) == (0, 0, 0)  # barras negras a los lados
    # con -50% la imagen mide 200x200 y desborda el cuadro: ya no hay barras
    for point in [(5, 50), (5, 5), (195, 95), (100, 50)]:
        assert con_margen.getpixel(point) == (255, 0, 0)


@pytest.mark.parametrize("margin", [MIN_MARGIN, -10, 0, 10, MAX_MARGIN])
def test_el_preview_mide_lo_pedido_con_cualquier_margen_y_sombra(margin):
    result = render_preview(red(), "ajustar", 160, 90, "desenfocado", True, margin, darkness=30)
    assert result.size == (160, 90)


def test_la_sombra_con_margen_negativo_no_falla():
    graph = build_filter_graph("ajustar", 1920, 1080, 30, "ninguno", True, -20)
    assert "[shadow]" in graph and graph.endswith("fps=30[v]")


# --- Exportación real -------------------------------------------------------------------


@pytest.fixture
def export_media(tmp_path):
    art = tmp_path / "art.png"
    Image.new("RGB", (400, 400), (30, 60, 200)).save(art)
    background = tmp_path / "white.png"
    Image.new("RGB", (400, 400), (255, 255, 255)).save(background)
    audio = make_wav(tmp_path / "a.wav", seconds=2, rate=8000)
    return art, background, audio


def frame_pixels(video, tmp_path, name="frame.png"):
    frame = tmp_path / name
    subprocess.run([get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", "1",
                    "-i", str(video), "-frames:v", "1", str(frame)], check=True)
    return Image.open(frame).convert("RGB")


@pytest.mark.parametrize("darkness, low, high", [(0, 240, 256), (50, 110, 146), (100, 0, 25)])
def test_el_fondo_exportado_es_mas_oscuro_con_mas_oscuridad(
        export_media, tmp_path, darkness, low, high):
    art, background, audio = export_media
    video = tmp_path / f"d{darkness}.mp4"
    export_video(art, audio, video, "16:9", 480, 1, "ajustar", duration=2,
                 background="personalizado", background_image=background, darkness=darkness)
    pixels = frame_pixels(video, tmp_path, f"d{darkness}.png")
    assert all(low <= channel < high for channel in pixels.getpixel((20, 240)))
    # el album art (azul) no se oscurece
    assert pixels.getpixel((427, 240))[2] > 150


def test_el_margen_negativo_acerca_la_imagen_en_el_video(export_media, tmp_path):
    art, _, audio = export_media
    normal, zoom = tmp_path / "normal.mp4", tmp_path / "zoom.mp4"
    export_video(art, audio, normal, "16:9", 480, 1, "ajustar", duration=2, margin=0)
    export_video(art, audio, zoom, "16:9", 480, 1, "ajustar", duration=2, margin=-20)
    # cuadro 854x480: sin margen la imagen mide 480x480 (x de 187 a 667)
    plain = frame_pixels(normal, tmp_path, "normal.png")
    assert max(plain.getpixel((100, 5))) < 30  # barra negra
    # con -20% mide 672x672 (x de 91 a 763) y llega al borde superior
    zoomed = frame_pixels(zoom, tmp_path, "zoom.png")
    assert zoomed.getpixel((100, 5))[2] > 150
    assert zoomed.getpixel((427, 5))[2] > 150
    assert max(zoomed.getpixel((20, 5))) < 30  # aún queda barra más allá de x=91


def test_exporta_con_margen_negativo_sombra_y_oscuridad(export_media, tmp_path):
    art, background, audio = export_media
    video = tmp_path / "todo.mp4"
    export_video(art, audio, video, "9:16", 480, 1, "ajustar", duration=2,
                 background="desenfocado", shadow=True, margin=-30, darkness=60)
    assert video.stat().st_size > 1000
    assert frame_pixels(video, tmp_path, "todo.png").size == (480, 854)
