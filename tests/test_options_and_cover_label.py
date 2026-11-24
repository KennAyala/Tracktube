"""UI: oscuridad del fondo, margen negativo y la etiqueta «Album art en metadata»."""
import time
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtGui import QColor, QPalette

from audio_helpers import embed_cover, image_bytes, make_audio, make_wav
from tracktube.core import media_info


@pytest.fixture
def media(tmp_path):
    image = tmp_path / "cover.png"
    Image.new("RGB", (200, 200), (10, 100, 200)).save(image)
    return str(image), str(make_wav(tmp_path / "track.wav"))


def wait_for_worker(qapp, window, timeout=60):
    deadline = time.monotonic() + timeout
    while window._worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()
    assert window._worker is None


# --- Oscuridad del fondo ------------------------------------------------------------


def set_background(window, key):
    window.combo_background.setCurrentIndex(window.combo_background.findData(key))


def test_la_oscuridad_siempre_se_muestra_pero_solo_se_habilita_con_fondo(qapp, make_window):
    window = make_window()
    window.show()
    qapp.processEvents()
    spin, label = window.spin_darkness, window.label_darkness
    assert spin.isVisible() and label.isVisible()
    assert (spin.minimum(), spin.maximum(), spin.value()) == (0, 100, 0)
    assert spin.suffix() == " %"

    assert not spin.isEnabled() and not label.isEnabled()  # sin fondo
    for background in ("desenfocado", "personalizado"):
        set_background(window, background)
        assert spin.isEnabled() and label.isEnabled() and spin.isVisible()
    set_background(window, "ninguno")
    assert not spin.isEnabled() and spin.isVisible()  # sigue visible, pero deshabilitada


def test_la_oscuridad_se_deshabilita_si_el_ajuste_no_usa_fondo(make_window):
    window = make_window()
    set_background(window, "desenfocado")
    assert window.spin_darkness.isEnabled()
    window.combo_fit.setCurrentIndex(window.combo_fit.findData("cortar"))
    assert not window.spin_darkness.isEnabled()
    window.combo_fit.setCurrentIndex(window.combo_fit.findData("ajustar"))
    assert window.spin_darkness.isEnabled()


def test_la_oscuridad_se_muestra_en_el_preview(make_window, media):
    window = make_window()
    window.slot_image.set_file(media[0])  # cuadrada azul (10, 100, 200)
    set_background(window, "desenfocado")

    def left_bar_color():
        return window.preview.canvas.pixmap().toImage().pixelColor(2, 100)

    claro = left_bar_color()
    window.spin_darkness.setValue(50)
    medio = left_bar_color()
    window.spin_darkness.setValue(100)
    negro = left_bar_color()
    assert abs(medio.blue() - claro.blue() * 0.5) <= 3
    assert (negro.red(), negro.green(), negro.blue()) == (0, 0, 0)


def test_la_oscuridad_y_el_margen_negativo_van_al_exportador(
        qapp, make_window, media, tmp_path, monkeypatch):
    from tracktube.ui import export_worker

    recibido = {}
    monkeypatch.setattr(export_worker, "export_video", lambda **params: recibido.update(params))
    window = make_window()
    window.slot_image.set_file(media[0])
    window.slot_audio.set_file(media[1])
    window.input_folder.setText(str(tmp_path))
    set_background(window, "desenfocado")
    window.spin_darkness.setValue(40)
    window.spin_margin.setValue(-15)
    window.btn_export.click()
    wait_for_worker(qapp, window)
    assert recibido["darkness"] == 40
    assert recibido["margin"] == -15
    assert recibido["background"] == "desenfocado"


def test_la_oscuridad_se_guarda_y_se_restaura(make_window):
    window = make_window()
    set_background(window, "desenfocado")
    window.spin_darkness.setValue(35)
    window.close()
    other = make_window()
    assert other.spin_darkness.value() == 35


def test_la_etiqueta_de_oscuridad_sigue_el_idioma(make_window):
    window = make_window()
    assert window.label_darkness.text() == "Background darkness"
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.label_darkness.text() == "Oscuridad del fondo"


# --- Margen negativo ------------------------------------------------------------------


def test_el_margen_acepta_negativos_y_el_boton_x_los_reinicia(make_window):
    window = make_window()
    spin = window.spin_margin
    assert spin.minimum() == -50 and spin.maximum() == 40
    spin.setValue(-25)
    assert spin.value() == -25
    window.btn_margin_reset.click()
    assert spin.value() == 0


def test_el_margen_negativo_se_guarda_y_se_restaura(make_window):
    window = make_window()
    window.spin_margin.setValue(-30)
    window.close()
    assert make_window().spin_margin.value() == -30


def test_el_margen_negativo_acerca_la_imagen_en_el_preview(make_window, media):
    window = make_window()
    window.slot_image.set_file(media[0])  # cuadrada en un cuadro 16:9

    def left_bar_color():
        return window.preview.canvas.pixmap().toImage().pixelColor(2, 100)

    assert left_bar_color().blue() == 0  # barra negra
    window.spin_margin.setValue(-50)
    assert left_bar_color().blue() == 200  # la imagen llega hasta el borde


# --- Etiqueta «Album art en metadata» ---------------------------------------------------


@pytest.fixture
def audio_with_cover(tmp_path):
    path = make_audio(tmp_path, "mp3", "con-caratula")
    embed_cover(path, "mp3", image_bytes("PNG", (300, 280), (10, 200, 30)), "image/png")
    return str(path)


def test_la_etiqueta_esta_oculta_sin_audio(qapp, make_window):
    window = make_window()
    window.show()
    qapp.processEvents()
    assert not window.slot_audio.label_cover.isVisible()


def test_la_etiqueta_dice_si_y_la_resolucion_en_verde(qapp, make_window, audio_with_cover):
    window = make_window()
    window.show()
    window.slot_audio.set_file(audio_with_cover)
    label = window.slot_audio.label_cover
    assert label.isVisible()
    assert label.text().startswith("Album art in metadata: ")
    assert "Yes (300 × 280)" in label.text()
    assert "#1a7f37" in label.text()  # verde (tema claro)


def test_la_etiqueta_dice_no_si_el_audio_no_trae_imagen(qapp, make_window, media):
    window = make_window()
    window.show()
    window.slot_audio.set_file(media[1])
    label = window.slot_audio.label_cover
    assert label.isVisible()
    assert label.text().startswith("Album art in metadata: ")
    assert ">No<" in label.text()
    assert "#cf222e" in label.text() and "#1a7f37" not in label.text()


def test_la_etiqueta_va_debajo_de_la_informacion_del_audio(qapp, make_window, audio_with_cover):
    window = make_window()
    window.show()
    window.slot_audio.set_file(audio_with_cover)
    qapp.processEvents()
    slot = window.slot_audio
    assert slot.label_cover.geometry().top() >= slot.info.geometry().bottom() - 2
    assert "Bit depth" in slot.info.text()  # la información que ya existía sigue ahí


def test_la_etiqueta_se_actualiza_al_cambiar_o_quitar_el_audio(
        qapp, make_window, audio_with_cover, media):
    window = make_window()
    window.show()
    slot = window.slot_audio
    slot.set_file(audio_with_cover)
    assert "Yes" in slot.label_cover.text()
    slot.set_file(media[1])
    assert ">No<" in slot.label_cover.text()
    slot.clear()
    assert not slot.label_cover.isVisible()


def test_la_etiqueta_sigue_el_idioma(make_window, audio_with_cover):
    window = make_window()
    window.slot_audio.set_file(audio_with_cover)
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    text = window.slot_audio.label_cover.text()
    assert text.startswith("Album art en metadata: ") and "Sí (300 × 280)" in text


def test_la_etiqueta_cambia_de_color_con_el_tema_oscuro(make_window, audio_with_cover, media):
    window = make_window()
    window.slot_audio.set_file(audio_with_cover)
    slot = window.slot_audio
    palette = slot.palette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    slot.setPalette(palette)
    assert "#3fb950" in slot.label_cover.text() and "#1a7f37" not in slot.label_cover.text()

    slot.set_file(media[1])  # sin imagen: rojo claro para fondo oscuro
    assert "#f85149" in slot.label_cover.text()

    palette.setColor(QPalette.Window, QColor(243, 243, 243))
    slot.setPalette(palette)
    assert "#cf222e" in slot.label_cover.text()


def test_una_imagen_incrustada_ilegible_dice_si_sin_resolucion(make_window, tmp_path):
    path = make_audio(tmp_path, "mp3", "corrupta")
    embed_cover(path, "mp3", b"esto no es una imagen", "image/png")
    assert media_info.get_embedded_cover(path).size is None
    window = make_window()
    window.slot_audio.set_file(str(path))
    text = window.slot_audio.label_cover.text()
    assert "Yes" in text and "×" not in text


def test_la_resolucion_de_la_imagen_incrustada(tmp_path):
    path = make_audio(tmp_path, "flac")
    embed_cover(path, "flac", image_bytes("JPEG", (640, 480)), "image/jpeg")
    assert media_info.get_embedded_cover(path).size == (640, 480)
    assert Path(path).is_file()
