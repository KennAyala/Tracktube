"""Desenfoque configurable del fondo y botones ✕ que solo aparecen si el valor cambió."""
import subprocess
import time

import pytest
from PIL import Image, ImageStat

from audio_helpers import make_wav
from tracktube.core.exporter import export_video, get_ffmpeg_exe
from tracktube.core.fit_modes import (
    DEFAULT_BLUR, MAX_BLUR, _blur_sigma, build_filter_graph, render_preview,
)


def stripes(size=100, width=2):
    """Franjas verticales blancas y negras: el desenfoque las va borrando."""
    image = Image.new("RGB", (size, size), (0, 0, 0))
    for x in range(0, size, width * 2):
        image.paste((255, 255, 255), (x, 0, x + width, size))
    return image


def contrast(image, box):
    """Desviación estándar de la luminosidad de una zona: baja cuando está desenfocada."""
    return ImageStat.Stat(image.crop(box).convert("L")).stddev[0]


# --- Núcleo --------------------------------------------------------------------------


def test_el_desenfoque_por_defecto_es_50():
    assert DEFAULT_BLUR == 50 and MAX_BLUR == 100


def test_al_50_por_ciento_el_desenfoque_es_el_de_siempre():
    # el 4% del lado corto, igual que antes de que fuera configurable
    assert _blur_sigma(1920, 1080) == pytest.approx(43.2)
    assert _blur_sigma(854, 480, 50) == pytest.approx(19.2)


@pytest.mark.parametrize("blur, sigma", [(0, "0.00"), (25, "21.60"), (50, "43.20"), (100, "86.40")])
def test_el_desenfoque_escala_la_desviacion_del_filtro(blur, sigma):
    graph = build_filter_graph("ajustar", 1920, 1080, 30, "desenfocado", blur=blur)
    if blur == 0:
        assert "gblur" not in graph  # 0% no desenfoca
    else:
        assert f"crop=1920:1080,gblur=sigma={sigma},format=rgba[bg]" in graph


def test_el_desenfoque_por_defecto_no_cambia_el_filtro():
    assert build_filter_graph("ajustar", 1920, 1080, 30, "desenfocado") \
        == build_filter_graph("ajustar", 1920, 1080, 30, "desenfocado", blur=50)


@pytest.mark.parametrize("background", ["ninguno", "personalizado"])
def test_el_desenfoque_solo_afecta_al_fondo_desenfocado(background):
    assert build_filter_graph("ajustar", 1920, 1080, 30, background, margin=10, blur=10) \
        == build_filter_graph("ajustar", 1920, 1080, 30, background, margin=10, blur=90)


def test_el_desenfoque_no_cambia_la_sombra():
    graph = build_filter_graph("ajustar", 1920, 1080, 30, "desenfocado", True, blur=100)
    assert "gblur=sigma=32.4[shadow]" in graph  # la sombra mantiene su propio desenfoque


def test_mas_desenfoque_borra_mas_detalle_en_el_preview():
    image = stripes()
    values = [
        contrast(render_preview(image, "ajustar", 200, 100, "desenfocado", blur=blur),
                 (0, 40, 40, 60))
        for blur in (0, 10, 30, 100)
    ]
    assert values == sorted(values, reverse=True)  # cada paso borra más detalle
    assert values[0] > 100 and values[-1] < 20


def test_el_preview_sin_desenfoque_conserva_el_fondo_nitido():
    image = stripes()
    sin = render_preview(image, "ajustar", 200, 100, "desenfocado", blur=0)
    assert contrast(sin, (0, 40, 40, 60)) > 100


def test_el_desenfoque_se_ignora_fuera_de_ajustar_y_sin_fondo_desenfocado():
    image = stripes()
    for kwargs in ({"mode": "cortar", "background": "desenfocado"},
                   {"mode": "ajustar", "background": "ninguno"}):
        a = render_preview(image, kwargs["mode"], 200, 100, kwargs["background"], blur=0)
        b = render_preview(image, kwargs["mode"], 200, 100, kwargs["background"], blur=100)
        assert a.tobytes() == b.tobytes()


def test_el_desenfoque_exportado_cambia_con_el_porcentaje(tmp_path):
    art = tmp_path / "stripes.png"
    stripes(400, 2).save(art)
    audio = make_wav(tmp_path / "a.wav", seconds=2, rate=8000)
    results = {}
    for blur in (0, 100):
        video = tmp_path / f"b{blur}.mp4"
        export_video(art, audio, video, "16:9", 480, 1, "ajustar", duration=2,
                     background="desenfocado", blur=blur)
        frame = tmp_path / f"b{blur}.png"
        subprocess.run([get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", "1",
                        "-i", str(video), "-frames:v", "1", str(frame)], check=True)
        # zona del fondo a la izquierda de la imagen (que mide 480x480 en el centro)
        results[blur] = contrast(Image.open(frame), (10, 200, 150, 260))
    assert results[0] > 60 and results[100] < 15 and results[0] > results[100]


# --- Interfaz: campo de desenfoque ------------------------------------------------------


def set_background(window, key):
    window.combo_background.setCurrentIndex(window.combo_background.findData(key))


def test_el_desenfoque_siempre_se_muestra_y_se_habilita_solo_con_fondo_desenfocado(
        qapp, make_window):
    window = make_window()
    window.show()
    qapp.processEvents()
    spin = window.spin_blur
    assert spin.isVisible() and window.label_blur.isVisible()
    assert (spin.minimum(), spin.maximum(), spin.value()) == (0, 100, 50)
    assert spin.suffix() == " %"

    assert not spin.isEnabled()  # sin fondo
    set_background(window, "personalizado")
    assert not spin.isEnabled()  # el desenfoque no aplica a una imagen propia
    set_background(window, "desenfocado")
    assert spin.isEnabled() and window.label_blur.isEnabled()
    window.combo_fit.setCurrentIndex(window.combo_fit.findData("cortar"))
    assert not spin.isEnabled() and spin.isVisible()


def test_la_etiqueta_y_los_tooltips_del_desenfoque_siguen_el_idioma(make_window):
    window = make_window()
    assert window.label_blur.text() == "Background blur"
    assert "Reset" in window.btn_blur_reset.toolTip()
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.label_blur.text() == "Desenfoque del fondo"
    assert "Restablecer" in window.btn_blur_reset.toolTip()
    assert "Restablecer" in window.btn_darkness_reset.toolTip()
    assert "Restablecer" in window.btn_margin_reset.toolTip()


def test_el_desenfoque_se_ve_en_el_preview(make_window, tmp_path):
    art = tmp_path / "stripes.png"
    stripes(100, 2).save(art)
    window = make_window()
    window.slot_image.set_file(str(art))
    set_background(window, "desenfocado")

    def bar_contrast():
        image = window.preview.canvas.pixmap().toImage()
        region = Image.frombytes("RGBA", (40, 20), bytes(image.copy(0, 100, 40, 20).constBits()),
                                 "raw", "BGRA").convert("L")
        return ImageStat.Stat(region).stddev[0]

    window.spin_blur.setValue(0)
    nitido = bar_contrast()
    window.spin_blur.setValue(100)
    assert bar_contrast() < nitido / 5


def test_el_desenfoque_se_guarda_y_se_restaura(make_window):
    window = make_window()
    window.spin_blur.setValue(20)
    window.close()
    assert make_window().spin_blur.value() == 20


def test_el_desenfoque_va_al_exportador(qapp, make_window, tmp_path, monkeypatch):
    from tracktube.ui import export_worker

    recibido = {}
    monkeypatch.setattr(export_worker, "export_video", lambda **params: recibido.update(params))
    image = tmp_path / "cover.png"
    Image.new("RGB", (200, 200), (10, 100, 200)).save(image)
    window = make_window()
    window.slot_image.set_file(str(image))
    window.slot_audio.set_file(str(make_wav(tmp_path / "t.wav")))
    window.input_folder.setText(str(tmp_path))
    set_background(window, "desenfocado")
    window.spin_blur.setValue(80)
    window.btn_export.click()
    deadline = time.monotonic() + 30
    while window._worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    assert recibido["blur"] == 80


# --- Interfaz: botones ✕ ------------------------------------------------------------------

RESETS = [
    # (spin, botón, valor por defecto, otro valor)
    ("spin_blur", "btn_blur_reset", 50, 20),
    ("spin_darkness", "btn_darkness_reset", 0, 30),
    ("spin_margin", "btn_margin_reset", 0, -15),
]


@pytest.mark.parametrize("spin_name, button_name, default, other", RESETS)
def test_la_x_solo_se_muestra_si_el_valor_no_es_el_de_por_defecto(
        make_window, spin_name, button_name, default, other):
    window = make_window()
    spin, button = getattr(window, spin_name), getattr(window, button_name)
    assert spin.value() == default
    assert not button.isVisibleTo(window)  # valor por defecto: sin X

    spin.setValue(other)
    assert button.isVisibleTo(window)  # valor distinto: con X

    spin.setValue(default)
    assert not button.isVisibleTo(window)  # vuelve al valor por defecto: la X desaparece


@pytest.mark.parametrize("spin_name, button_name, default, other", RESETS)
def test_la_x_devuelve_el_valor_por_defecto_y_se_oculta(
        make_window, spin_name, button_name, default, other):
    window = make_window()
    set_background(window, "desenfocado")  # sin fondo los campos y sus X están deshabilitados
    spin, button = getattr(window, spin_name), getattr(window, button_name)
    spin.setValue(other)
    button.click()
    assert spin.value() == default
    assert not button.isVisibleTo(window)


@pytest.mark.parametrize("spin_name, button_name, default, other", RESETS)
def test_la_x_aparece_al_abrir_si_el_valor_guardado_no_es_el_de_por_defecto(
        make_window, spin_name, button_name, default, other):
    window = make_window()
    getattr(window, spin_name).setValue(other)
    window.close()

    reopened = make_window()
    assert getattr(reopened, spin_name).value() == other
    assert getattr(reopened, button_name).isVisibleTo(reopened)


def test_las_x_se_muestran_en_la_ventana_real(qapp, make_window):
    window = make_window()
    window.show()
    qapp.processEvents()
    assert not any(b.isVisible() for b in (
        window.btn_blur_reset, window.btn_darkness_reset, window.btn_margin_reset))
    set_background(window, "desenfocado")
    window.spin_blur.setValue(10)
    window.spin_darkness.setValue(10)
    window.spin_margin.setValue(10)
    assert all(b.isVisible() for b in (
        window.btn_blur_reset, window.btn_darkness_reset, window.btn_margin_reset))


def test_cada_x_esta_a_la_altura_de_su_campo(qapp, make_window):
    window = make_window()
    window.show()
    set_background(window, "desenfocado")
    for spin, button in ((window.spin_blur, window.btn_blur_reset),
                         (window.spin_darkness, window.btn_darkness_reset),
                         (window.spin_margin, window.btn_margin_reset)):
        spin.setValue(spin.value() + 10)
    qapp.processEvents()
    for spin, button in ((window.spin_blur, window.btn_blur_reset),
                         (window.spin_darkness, window.btn_darkness_reset),
                         (window.spin_margin, window.btn_margin_reset)):
        assert abs(spin.geometry().center().y() - button.geometry().center().y()) <= 3


def test_al_aparecer_las_x_el_resto_de_los_campos_no_se_mueve(qapp, make_window):
    window = make_window()
    window.show()
    set_background(window, "desenfocado")
    qapp.processEvents()
    widgets = [window.spin_blur, window.spin_darkness, window.spin_margin,
               window.combo_resolution, window.label_dimensions, window.combo_fit]
    before = [w.geometry() for w in widgets]
    for spin in (window.spin_blur, window.spin_darkness, window.spin_margin):
        spin.setValue(spin.value() + 10)  # aparecen las tres X
    qapp.processEvents()
    assert [w.geometry() for w in widgets] == before
    for spin in (window.spin_blur, window.spin_darkness, window.spin_margin):
        spin.setValue(spin.value() - 10)  # y vuelven a ocultarse
    qapp.processEvents()
    assert [w.geometry() for w in widgets] == before


def test_la_sombra_va_debajo_del_margen(qapp, make_window):
    window = make_window()
    window.show()
    qapp.processEvents()
    margin, shadow = window.spin_margin.geometry(), window.check_shadow.geometry()
    fps = window.label_fps.geometry()
    assert shadow.top() > margin.bottom()  # la sombra debajo del margen
    assert fps.top() > shadow.bottom()  # y los FPS al final, debajo de la sombra
    assert shadow.left() < window.spin_margin.geometry().right()  # en la misma columna


def test_la_x_sigue_el_estado_de_su_campo(qapp, make_window):
    window = make_window()
    window.show()
    set_background(window, "desenfocado")
    window.spin_blur.setValue(20)
    window.spin_darkness.setValue(30)
    assert window.btn_blur_reset.isEnabled() and window.btn_darkness_reset.isEnabled()

    set_background(window, "personalizado")  # el desenfoque ya no aplica, la oscuridad sí
    assert not window.btn_blur_reset.isEnabled() and window.btn_blur_reset.isVisible()
    assert window.btn_darkness_reset.isEnabled()

    set_background(window, "ninguno")  # sin fondo: ninguna aplica, pero las X se siguen viendo
    assert not window.btn_darkness_reset.isEnabled() and window.btn_darkness_reset.isVisible()
