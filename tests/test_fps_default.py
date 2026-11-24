"""FPS: el valor por defecto es 1 y las opciones son solo números."""
import time

import pytest
from PIL import Image

from audio_helpers import make_wav
from tracktube import i18n
from tracktube.core import presets


def radio_texts(window):
    group = window.fps_group
    return {group.id(button): button.text() for button in group.buttons()}


def test_las_opciones_de_fps_y_el_valor_por_defecto():
    assert presets.FPS_OPTIONS == (1, 15, 24, 30, 60)
    assert presets.DEFAULT_FPS == 1


def test_el_fps_por_defecto_en_la_interfaz_es_1(make_window):
    window = make_window()
    assert window.fps_group.checkedId() == 1
    assert [b.isChecked() for b in window.fps_group.buttons()] == [True, False, False, False, False]


def test_los_botones_de_fps_son_solo_numeros(make_window):
    window = make_window()
    assert radio_texts(window) == {1: "1", 15: "15", 24: "24", 30: "30", 60: "60"}


def test_el_texto_minimo_ya_no_existe_en_ningun_idioma(make_window):
    window = make_window()
    for code in ("en", "es"):
        window.combo_language.setCurrentIndex(window.combo_language.findData(code))
        assert radio_texts(window) == {1: "1", 15: "15", 24: "24", 30: "30", 60: "60"}
        assert not any("min" in text.lower() for text in radio_texts(window).values())
    assert "settings.fps_min" not in i18n.STRINGS["en"]
    assert "settings.fps_min" not in i18n.STRINGS["es"]


def test_el_primer_boton_de_fps_es_el_1(make_window):
    window = make_window()
    assert [b.text() for b in window.fps_group.buttons()] == ["1", "15", "24", "30", "60"]


def test_un_fps_guardado_se_restaura(make_window):
    window = make_window()
    window.fps_group.button(30).click()
    assert window.fps_group.checkedId() == 30
    window.close()
    assert make_window().fps_group.checkedId() == 30


def test_la_exportacion_usa_1_fps_por_defecto(qapp, make_window, tmp_path, monkeypatch):
    from tracktube.ui import export_worker

    recibido = {}
    monkeypatch.setattr(export_worker, "export_video", lambda **params: recibido.update(params))
    image = tmp_path / "cover.png"
    Image.new("RGB", (200, 200), (10, 100, 200)).save(image)
    window = make_window()
    window.slot_image.set_file(str(image))
    window.slot_audio.set_file(str(make_wav(tmp_path / "t.wav")))
    window.input_folder.setText(str(tmp_path))
    window.btn_export.click()
    deadline = time.monotonic() + 30
    while window._worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    assert recibido["fps"] == 1


@pytest.mark.parametrize("fps, gop, bitrate", [(1, 1, 8000), (30, 15, 8000), (60, 30, 12000)])
def test_los_fps_siguen_marcando_el_gop_y_el_bitrate(fps, gop, bitrate):
    assert presets.get_gop(fps) == gop
    assert presets.get_video_bitrate_kbps(1080, fps) == bitrate
