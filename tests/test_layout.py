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


# --- Columna izquierda: audio, imagen y, debajo, los ajustes de salida ---------------------


def test_los_ajustes_estan_debajo_de_los_inputs_en_la_columna_izquierda(window):
    audio, image = box(window.slot_audio, window), box(window.slot_image, window)
    settings = box(window.group_settings, window)
    assert audio.bottom() < image.top() < image.bottom() < settings.top()
    assert settings.top() - image.bottom() < 30  # pegados, sin hueco
    # los tres ocupan la misma columna, con el mismo ancho
    assert audio.left() == image.left() == settings.left()
    assert audio.width() == image.width() == settings.width()


def test_la_vista_previa_esta_a_la_derecha_de_la_columna_izquierda(window):
    preview = box(window.preview, window)
    for widget in (window.slot_audio, window.slot_image, window.group_settings):
        assert preview.left() > box(widget, window).right()
    assert abs(preview.top() - box(window.slot_audio, window).top()) <= 2  # arrancan juntas


def test_la_vista_previa_ocupa_toda_la_altura_de_las_dos_columnas(window):
    preview, settings = box(window.preview, window), box(window.group_settings, window)
    assert abs(preview.bottom() - settings.bottom()) <= 3


def test_los_ajustes_ya_no_estan_arriba_de_la_vista_previa(window):
    settings, preview = box(window.group_settings, window), box(window.preview, window)
    assert not (settings.left() == preview.left() and settings.bottom() < preview.top())
    assert settings.right() < preview.left()


def test_la_altura_la_fija_la_columna_izquierda_y_es_baja(qapp, window):
    # los ajustes ya no se apilan sobre la vista previa: la altura depende de la columna
    # izquierda, que con los inputs vacíos es corta
    window.adjustSize()
    settle(qapp)
    left_height = box(window.group_settings, window).bottom() - box(window.slot_audio, window).top()
    assert left_height < 360
    assert box(window.group_export, window).bottom() - box(window.slot_audio, window).top() < 560


# --- Ajustes de salida en dos columnas ----------------------------------------------------------


def left_column(window):
    """Formato del video, con su margen, su sombra y los FPS al final."""
    return [window.label_ratio, window.combo_ratio, window.label_resolution,
            window.combo_resolution, window.label_fit, window.combo_fit,
            window.label_margin, window.spin_margin, window.check_shadow, window.label_fps]


def right_column(window):
    """Fondo con su desenfoque y su oscuridad."""
    return [window.label_background, window.combo_background, window.label_blur,
            window.spin_blur, window.label_darkness, window.spin_darkness]


def test_los_ajustes_estan_en_dos_columnas(window):
    left_edge = max(box(w, window).right() for w in left_column(window))
    right_edge = min(box(w, window).left() for w in right_column(window))
    assert left_edge < right_edge  # nada de una columna invade a la otra
    assert box(window.label_ratio, window).left() < box(window.label_background, window).left()


def test_columna_izquierda_en_orden(window):
    tops = [box(w, window).top() for w in (
        window.combo_ratio, window.combo_resolution, window.combo_fit,
        window.spin_margin, window.check_shadow, window.label_fps)]
    # relación de aspecto, resolución, ajuste de imagen, margen, sombra y FPS
    assert tops == sorted(tops) and len(set(tops)) == 6


def test_columna_derecha_en_orden(window):
    tops = [box(w, window).top() for w in (
        window.combo_background, window.spin_blur, window.spin_darkness)]
    assert tops == sorted(tops) and len(set(tops)) == 3  # fondo, desenfoque, oscuridad


def test_el_margen_va_debajo_del_ajuste_de_imagen(window):
    fit, margin = box(window.combo_fit, window), box(window.spin_margin, window)
    assert margin.top() > fit.bottom()
    assert margin.top() - fit.bottom() < 20  # pegado, sin hueco
    assert margin.left() == fit.left()  # misma columna de campos
    assert box(window.label_margin, window).left() == box(window.label_fit, window).left()


def test_la_sombra_va_debajo_del_margen_y_pegada_a_la_izquierda(window):
    margin, shadow = box(window.spin_margin, window), box(window.check_shadow, window)
    assert shadow.top() > margin.bottom()
    assert shadow.top() - margin.bottom() < 20
    assert abs(shadow.left() - box(window.label_margin, window).left()) <= 6  # junto a las etiquetas


def test_los_fps_van_hasta_abajo_y_pegados_a_la_izquierda(window):
    fps_label, fit = box(window.label_fps, window), box(window.combo_fit, window)
    radios = [box(button, window) for button in window.fps_group.buttons()]
    # hasta abajo: debajo de todo lo demás de la sección
    others = [w for w in left_column(window) + right_column(window) if w is not window.label_fps]
    assert fps_label.top() > max(box(w, window).bottom() for w in others) - 4
    assert fps_label.top() > box(window.check_shadow, window).bottom()
    # pegados a la izquierda: la etiqueta con las demás etiquetas y los botones con los campos
    assert fps_label.left() == box(window.label_ratio, window).left()
    assert abs(radios[0].left() - fit.left()) <= 6
    assert [r.left() for r in radios] == sorted(r.left() for r in radios)  # 1, 15, 24, 30, 60
    # y no se van hacia la columna derecha
    assert max(r.right() for r in radios) < box(window.combo_background, window).left()


def test_los_fps_estan_en_la_misma_linea_que_su_etiqueta(window):
    label = box(window.label_fps, window)
    for button in window.fps_group.buttons():
        assert abs(box(button, window).center().y() - label.center().y()) <= 6


def test_las_dos_columnas_arrancan_a_la_misma_altura(window):
    assert abs(box(window.label_ratio, window).top()
               - box(window.label_background, window).top()) <= 8


def test_las_filas_estan_juntas_y_no_estiradas(window):
    """Guarda contra el espaciado heredado de 24 px que separaba las filas unos 50 px."""
    for first, second in ((window.combo_ratio, window.combo_resolution),
                          (window.combo_resolution, window.combo_fit),
                          (window.combo_fit, window.spin_margin),
                          (window.combo_background, window.spin_blur),
                          (window.spin_blur, window.spin_darkness)):
        step = box(second, window).top() - box(first, window).top()
        assert 20 <= step <= 42, f"filas a {step} px"


def test_la_seccion_de_ajustes_es_baja(window):
    # en una sola columna medía 322 px; en dos columnas debe quedar bastante más baja
    assert window.group_settings.height() < 270


def test_el_fondo_personalizado_solo_agrega_una_fila_a_su_columna(qapp, window):
    before = window.group_settings.height()
    window.combo_background.setCurrentIndex(window.combo_background.findData("personalizado"))
    settle(qapp)
    assert window.background_row.isVisible()
    # la columna derecha es más corta que la izquierda: la fila nueva cabe sin crecer mucho
    assert 0 <= window.group_settings.height() - before < 60
    # la fila nueva queda en la columna derecha, entre el fondo y el desenfoque
    row = box(window.background_row, window)
    assert box(window.combo_background, window).bottom() <= row.top()
    assert row.bottom() <= box(window.spin_blur, window).top() + 2
    assert row.left() > box(window.combo_ratio, window).right()


# --- Exportar a todo lo ancho ------------------------------------------------------------


def test_exportar_abarca_todo_el_ancho(window):
    export = box(window.group_export, window)
    left_edge = box(window.slot_audio, window).left()
    right_edge = max(box(window.preview, window).right(), box(window.group_settings, window).right())
    assert export.left() <= left_edge + 2
    assert export.right() >= right_edge - 2
    # abarca las dos columnas: es más ancha que cualquiera de ellas
    assert export.width() > box(window.preview, window).width()
    assert export.width() > box(window.slot_audio, window).width() * 1.3


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
    assert box(window.preview, window).right() < log.left()
    assert log.top() <= box(window.slot_audio, window).top() + 2


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
