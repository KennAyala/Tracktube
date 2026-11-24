"""Diseño de la ventana: ajustes de salida sobre la vista previa y Exportar a todo lo ancho."""
import time

import pytest
from PIL import Image

from tracktube.ui.preview_widget import PREVIEW_MIN


def settle(qapp, seconds=0.25):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)


@pytest.fixture
def window(qapp, make_window):
    window = make_window()
    window.show()
    settle(qapp)
    return window


def box(widget, parent):
    """Rectángulo del widget en coordenadas de la ventana."""
    top_left = widget.mapTo(parent, widget.rect().topLeft())
    rect = widget.rect()
    rect.moveTopLeft(top_left)
    return rect


# --- Título --------------------------------------------------------------------------


def test_los_ajustes_se_llaman_ajustes_de_salida(make_window):
    window = make_window()
    assert window.group_settings.title() == "Output settings"
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.group_settings.title() == "Ajustes de salida"
    window.combo_language.setCurrentIndex(window.combo_language.findData("en"))
    assert window.group_settings.title() == "Output settings"


# --- Ajustes de salida a la derecha, justo arriba de la vista previa -------------------


def test_los_ajustes_estan_a_la_derecha_del_audio_y_de_la_imagen(window):
    settings = box(window.group_settings, window)
    for slot in (window.slot_audio, window.slot_image):
        assert settings.left() > box(slot, window).right()
        assert settings.top() <= box(slot, window).top() + 2  # arrancan a la misma altura


def test_los_ajustes_estan_justo_arriba_de_la_vista_previa(window):
    settings, preview = box(window.group_settings, window), box(window.preview, window)
    assert settings.bottom() < preview.top()
    assert preview.top() - settings.bottom() < 30  # pegados, sin hueco
    assert (settings.left(), settings.width()) == (preview.left(), preview.width())  # misma columna


def test_la_columna_izquierda_solo_tiene_audio_e_imagen(window):
    audio, image = box(window.slot_audio, window), box(window.slot_image, window)
    settings = box(window.group_settings, window)
    assert audio.bottom() < image.top()
    assert audio.left() == image.left() and audio.left() < settings.left()
    # nada más ocupa esa columna entre la imagen y Exportar
    assert box(window.group_export, window).top() > image.bottom()


# --- Exportar a todo lo ancho ------------------------------------------------------------


def test_exportar_abarca_todo_el_ancho(window):
    export = box(window.group_export, window)
    left_edge = box(window.slot_audio, window).left()
    right_edge = max(box(window.preview, window).right(), box(window.group_settings, window).right())
    assert export.left() <= left_edge + 2
    assert export.right() >= right_edge - 2
    # abarca las dos columnas: es bastante más ancha que cualquiera de ellas
    assert export.width() > box(window.preview, window).width() * 1.3
    assert export.width() > box(window.slot_audio, window).width() * 3


def test_exportar_va_debajo_de_las_dos_columnas(window):
    export = box(window.group_export, window)
    for widget in (window.slot_image, window.group_settings, window.preview):
        assert export.top() > box(widget, window).bottom()


def test_el_aviso_de_short_va_a_todo_lo_ancho_justo_arriba_de_exportar(qapp, window):
    window.btn_vertical.click()
    window._duration = 60  # un video corto en vertical
    window._update_short_warning()
    settle(qapp)
    warning, export = box(window.label_short_warning, window), box(window.group_export, window)
    assert window.label_short_warning.isVisible()
    assert warning.bottom() < export.top() and export.top() - warning.bottom() < 30
    assert (warning.left(), warning.right()) == (export.left(), export.right())


def test_con_el_log_abierto_exportar_no_pasa_por_debajo_del_panel(qapp, window):
    window.btn_log.click()
    settle(qapp)
    export, log = box(window.group_export, window), box(window.log_panel, window)
    assert window.log_panel.isVisible()
    assert export.right() < log.left()  # el log queda a la derecha de todo
    assert log.top() <= box(window.group_settings, window).top() + 2


# --- La vista previa se adapta al espacio ------------------------------------------------------


@pytest.fixture
def with_image(window, tmp_path):
    path = tmp_path / "cover.png"
    Image.new("RGB", (300, 300), (10, 100, 200)).save(path)
    window.slot_image.set_file(str(path))
    return window


def pixmap_size(window):
    pixmap = window.preview.canvas.pixmap()
    return pixmap.width(), pixmap.height()


def test_la_vista_previa_cabe_en_su_espacio(qapp, with_image):
    window = with_image
    settle(qapp)
    width, height = pixmap_size(window)
    assert width <= window.preview.canvas.width() and height <= window.preview.canvas.height()
    assert abs(width / height - 16 / 9) < 0.05  # respeta el ratio


@pytest.mark.parametrize("vertical", [False, True])
def test_la_vista_previa_respeta_el_ratio_en_horizontal_y_vertical(qapp, with_image, vertical):
    window = with_image
    if vertical:
        window.btn_vertical.click()
    settle(qapp)
    width, height = pixmap_size(window)
    expected = 9 / 16 if vertical else 16 / 9
    assert abs(width / height - expected) < 0.05
    assert width <= window.preview.canvas.width() and height <= window.preview.canvas.height()


def test_la_vista_previa_crece_al_agrandar_la_ventana(qapp, with_image):
    window = with_image
    settle(qapp)
    before = pixmap_size(window)
    window.resize(window.width() + 400, window.height() + 300)
    settle(qapp, 0.5)
    after = pixmap_size(window)
    assert after[0] > before[0] and after[1] > before[1]


def test_la_vista_previa_no_baja_del_minimo_y_la_ventana_puede_ser_baja(qapp, with_image):
    window = with_image
    window.resize(window.minimumSizeHint())
    settle(qapp, 0.5)
    assert window.preview.canvas.width() >= PREVIEW_MIN[0]
    assert window.preview.canvas.height() >= PREVIEW_MIN[1]
    width, height = pixmap_size(window)
    assert width >= 2 and height >= 2


def test_el_lienzo_ya_no_fuerza_400_por_400(window):
    canvas = window.preview.canvas
    assert canvas.minimumSize().width() == PREVIEW_MIN[0]
    assert canvas.minimumSize().height() == PREVIEW_MIN[1]
    assert canvas.maximumSize().width() > 1000  # puede crecer


def test_exportar_la_vista_previa_sigue_usando_la_resolucion_del_video(
        qapp, with_image, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QFileDialog

    window = with_image
    window.resize(window.width() + 300, window.height() + 200)  # la vista previa en pantalla cambia
    settle(qapp, 0.4)
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *args: (str(tmp_path / "salida.png"), "PNG (*.png)"))
    window.preview.btn_export_image.click()
    with Image.open(tmp_path / "salida.png") as image:
        assert image.size == (1920, 1080)  # no depende del tamaño de la ventana
