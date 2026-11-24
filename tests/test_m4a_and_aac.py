"""Compatibilidad con .m4a (AAC y ALAC) y .aac."""
import time
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QMimeData, QUrl

from audio_helpers import embed_cover, image_bytes, make_audio
from tracktube.config import AUDIO_EXTENSIONS
from tracktube.core.exporter import export_video
from tracktube.core.media_info import get_audio_info, get_embedded_cover


# --- Extensiones ----------------------------------------------------------------------


def test_se_aceptan_m4a_y_aac():
    assert {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac"} == set(AUDIO_EXTENSIONS)


class FakeDrop:
    def __init__(self, path):
        self._mime = QMimeData()
        self._mime.setUrls([QUrl.fromLocalFile(str(path))])

    def mimeData(self):
        return self._mime


@pytest.mark.parametrize("name, accepted", [
    ("a.m4a", True), ("a.AAC", True), ("a.mp3", True), ("a.mp4", False), ("a.wma", False),
])
def test_arrastrar_y_soltar_acepta_m4a_y_aac(qapp, make_window, tmp_path, name, accepted):
    slot = make_window().slot_audio
    path = tmp_path / name
    path.write_bytes(b"x")
    assert (slot._dropped_path(FakeDrop(path)) is not None) is accepted


def test_el_dialogo_de_abrir_lista_m4a_y_aac(make_window, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    seen = {}

    def fake(parent, title, start, filters, *args):
        seen["filters"] = filters
        return "", ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake)
    make_window().slot_audio.btn_choose.click()
    assert "*.m4a" in seen["filters"] and "*.aac" in seen["filters"]


# --- Información del audio -----------------------------------------------------------------


def test_info_de_un_m4a_con_aac(tmp_path):
    info = get_audio_info(make_audio(tmp_path, "m4a", tone=True))
    assert info.format == "M4A (AAC)"
    assert info.duration == pytest.approx(2, abs=0.1)
    assert info.bit_depth is None  # AAC es con pérdida: no tiene profundidad de bits
    assert 64_000 < info.bitrate < 200_000


def test_info_de_un_m4a_alac_es_sin_perdida(tmp_path):
    info = get_audio_info(make_audio(tmp_path, "alac"))
    assert info.format == "M4A (ALAC)"
    assert info.bit_depth == 16
    assert info.duration == pytest.approx(2, abs=0.1)
    assert info.bitrate and info.bitrate > 100_000


def test_info_de_un_aac_sin_contenedor(tmp_path):
    info = get_audio_info(make_audio(tmp_path, "aac", tone=True))
    assert info.format == "AAC"
    assert info.duration == pytest.approx(2, abs=0.15)
    assert info.bit_depth is None
    assert isinstance(info.bitrate, int) and 64_000 < info.bitrate < 200_000


def test_un_archivo_m4a_corrupto_lanza_value_error(tmp_path):
    path = tmp_path / "roto.m4a"
    path.write_bytes(b"esto no es un audio")
    with pytest.raises(ValueError):
        get_audio_info(path)


# --- Imagen en los tags -----------------------------------------------------------------------


@pytest.mark.parametrize("key", ["m4a", "alac"])
@pytest.mark.parametrize("format, mime", [("PNG", "image/png"), ("JPEG", "image/jpeg")])
def test_encuentra_la_caratula_de_un_m4a(tmp_path, key, format, mime):
    path = make_audio(tmp_path, key)
    data = image_bytes(format, (150, 90))
    embed_cover(path, key, data, mime)
    cover = get_embedded_cover(path)
    assert cover is not None and cover.data == data
    assert cover.mime == mime and cover.size == (150, 90)


def test_un_m4a_sin_caratula_devuelve_none(tmp_path):
    assert get_embedded_cover(make_audio(tmp_path, "m4a")) is None


def test_un_aac_sin_contenedor_no_tiene_caratula(tmp_path):
    assert get_embedded_cover(make_audio(tmp_path, "aac")) is None


# --- Interfaz -------------------------------------------------------------------------------------


def test_la_interfaz_muestra_la_informacion_de_un_m4a(make_window, tmp_path):
    window = make_window()
    window.slot_audio.set_file(str(make_audio(tmp_path, "m4a", tone=True)))
    text = window.slot_audio.info.text()
    assert "Format: M4A (AAC)" in text and "Bit depth: —" in text and "Duration: 0:02" in text


def test_la_interfaz_muestra_la_informacion_de_un_m4a_alac(make_window, tmp_path):
    window = make_window()
    window.slot_audio.set_file(str(make_audio(tmp_path, "alac")))
    text = window.slot_audio.info.text()
    assert "Format: M4A (ALAC)" in text and "Bit depth: 16-bit" in text


def test_la_interfaz_muestra_la_informacion_de_un_aac(make_window, tmp_path):
    window = make_window()
    window.slot_audio.set_file(str(make_audio(tmp_path, "aac", tone=True)))
    text = window.slot_audio.info.text()
    assert "Format: AAC" in text and "Bit depth: —" in text


def test_un_m4a_con_caratula_muestra_la_etiqueta_y_el_boton(make_window, tmp_path):
    path = make_audio(tmp_path, "m4a")
    embed_cover(path, "m4a", image_bytes("PNG", (300, 300), (10, 200, 30)), "image/png")
    window = make_window()
    window.show()
    window.slot_audio.set_file(str(path))
    assert "Yes (300 × 300)" in window.slot_audio.label_cover.text()
    assert window.slot_image.btn_metadata.isVisible()
    window.slot_image.btn_metadata.click()
    assert window._image.size == (300, 300)


def test_el_reproductor_recibe_los_archivos_m4a_y_aac(make_window, tmp_path):
    window = make_window()
    for key in ("m4a", "aac"):
        path = make_audio(tmp_path, key, name=f"audio-{key}")
        window.slot_audio.set_file(str(path))
        assert Path(window.slot_audio.player.source().toLocalFile()) == Path(path)
        assert window.slot_audio.btn_play.isVisibleTo(window)


# --- Exportación real -------------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["m4a", "alac", "aac"])
def test_exporta_un_video_desde_m4a_y_aac(tmp_path, key):
    art = tmp_path / "art.png"
    Image.new("RGB", (200, 200), (30, 60, 200)).save(art)
    audio = make_audio(tmp_path, key, tone=(key != "alac"))
    video = tmp_path / f"{key}.mp4"
    export_video(art, audio, video, "16:9", 480, 15, "ajustar",
                 duration=get_audio_info(audio).duration)
    assert video.stat().st_size > 1000

    import subprocess

    from tracktube.core.exporter import get_ffmpeg_exe
    info = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(video)],
                          capture_output=True, text=True).stderr
    assert "aac (LC)" in info and "48000 Hz, stereo" in info
    assert "h264 (High)" in info and "854x480" in info


def test_exporta_desde_la_interfaz_con_un_m4a_con_caratula(qapp, make_window, tmp_path):
    path = make_audio(tmp_path, "m4a", tone=True)
    embed_cover(path, "m4a", image_bytes("JPEG", (300, 300), (200, 30, 30)), "image/jpeg")
    window = make_window()
    window.slot_audio.set_file(str(path))
    window.slot_image.btn_metadata.click()
    window.combo_resolution.setCurrentIndex(0)
    window.input_folder.setText(str(tmp_path))
    window.input_filename.setText("desde-m4a.mp4")
    window.btn_export.click()
    deadline = time.monotonic() + 60
    while window._worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    assert (tmp_path / "desde-m4a.mp4").stat().st_size > 1000
