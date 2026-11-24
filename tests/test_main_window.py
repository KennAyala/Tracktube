import subprocess
import time
import uuid
import wave
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtMultimedia import QMediaPlayer

from tracktube.core.exporter import get_ffmpeg_exe
from tracktube.ui.main_window import UUID_PATTERN


def new_uuid_name():
    return f"{uuid.uuid4()}.mp4"


def save_settings(settings_file, **values):
    settings = QSettings(settings_file, QSettings.IniFormat)
    for key, value in values.items():
        settings.setValue(key, value)
    settings.sync()


def stem(window):
    return Path(window.input_filename.text()).stem


def make_wav(path, seconds=2, rate=8000, bits=16):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(bits // 8)
        wav.setframerate(rate)
        wav.writeframes(b"\x00" * (bits // 8) * rate * seconds)


@pytest.fixture
def media(tmp_path):
    image = tmp_path / "cover.png"
    Image.new("RGB", (200, 200), (10, 100, 200)).save(image)
    audio = tmp_path / "track.wav"
    make_wav(audio)
    return str(image), str(audio)


def wait_for_worker(qapp, window, timeout=60):
    deadline = time.monotonic() + timeout
    while window._worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()
    assert window._worker is None, "la exportación no terminó"


# --- Carpeta y nombre de archivo -----------------------------------------------


def test_por_defecto_la_carpeta_es_exports_y_el_nombre_un_uuid(make_window):
    window = make_window()
    assert window.input_folder.text() == "exports"
    assert window.input_filename.text().endswith(".mp4")
    assert UUID_PATTERN.match(stem(window))


def test_el_boton_de_refrescar_esta_a_la_altura_del_nombre(qapp, make_window):
    window = make_window()
    window.show()
    qapp.processEvents()
    refresh_y = window.btn_refresh_uuid.geometry().center().y()
    assert abs(refresh_y - window.input_filename.geometry().center().y()) <= 3
    assert abs(refresh_y - window.input_folder.geometry().center().y()) > 10
    # y el botón de cambiar carpeta, a la altura de la carpeta
    assert abs(window.btn_folder.geometry().center().y()
               - window.input_folder.geometry().center().y()) <= 3


def test_la_ruta_final_une_carpeta_y_nombre(make_window, tmp_path, monkeypatch):
    window = make_window()
    window.input_folder.setText(str(tmp_path))
    window.input_filename.setText("mi-video.mp4")
    from tracktube.core import export_path
    assert export_path.build_path(
        window.input_folder.text(), window.input_filename.text()) == tmp_path / "mi-video.mp4"


def test_cambiar_carpeta_no_toca_el_nombre(make_window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    window = make_window()
    name = window.input_filename.text()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    window.btn_folder.click()
    assert window.input_folder.text() == str(tmp_path)
    assert window.input_filename.text() == name


def test_carpeta_y_nombre_se_guardan_y_restauran(make_window):
    window = make_window()
    window.input_folder.setText("D:/musica")
    window.input_filename.setText("mi-video.mp4")
    window.close()

    other = make_window()
    assert other.input_folder.text() == "D:/musica"
    assert other.input_filename.text() == "mi-video.mp4"


def test_se_migra_la_ruta_guardada_por_la_version_anterior(make_window, settings_file):
    save_settings(settings_file, export_path=f"D:/musica/{new_uuid_name()}")
    window = make_window()
    assert Path(window.input_folder.text()) == Path("D:/musica")
    assert UUID_PATTERN.match(stem(window))


# --- UUID ------------------------------------------------------------------


def test_el_uuid_cambia_cada_vez_que_se_abre_la_app(make_window, settings_file):
    old_name = new_uuid_name()
    save_settings(settings_file, export_folder="D:/musica", export_filename=old_name)
    window = make_window()
    assert window.input_filename.text() != old_name
    assert UUID_PATTERN.match(stem(window))
    assert window.input_folder.text() == "D:/musica"  # conserva la carpeta


def test_nombre_propio_se_respeta_al_abrir(make_window, settings_file):
    save_settings(settings_file, export_folder="D:/musica", export_filename="mi-video.mp4")
    assert make_window().input_filename.text() == "mi-video.mp4"


def test_el_uuid_cambia_al_terminar_la_exportacion(make_window, tmp_path):
    window = make_window()
    original = window.input_filename.text()
    window._output = tmp_path / "x.mp4"
    window._on_export_succeeded()
    assert window.input_filename.text() != original
    assert UUID_PATTERN.match(stem(window))


def test_el_estado_de_la_exportacion_se_muestra_en_una_etiqueta(make_window):
    window = make_window()
    assert window.label_progress.text() == "Ready"
    window._set_progress_state("running", 0)
    window.progress.setValue(45)
    assert window.label_progress.text() == "Exporting… 45%"
    window._set_progress_state("done", 100)
    assert window.label_progress.text() == "Done"
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.label_progress.text() == "Completado"
    window._set_progress_state("idle", 0)
    assert window.label_progress.text() == "Listo"


def test_no_muestra_aviso_al_terminar_la_exportacion(make_window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    window = make_window()
    monkeypatch.setattr(QMessageBox, "exec",
                        lambda self: pytest.fail("no debía mostrar ningún aviso"))
    window._output = tmp_path / "x.mp4"
    window._on_export_succeeded()
    assert window.progress.value() == 100
    assert window.progress.format() == "Done"


def test_nombre_propio_se_respeta_al_terminar(make_window, tmp_path):
    window = make_window()
    window.input_filename.setText("mi-video.mp4")
    window._output = tmp_path / "x.mp4"
    window._on_export_succeeded()
    assert window.input_filename.text() == "mi-video.mp4"


def test_boton_refrescar_cambia_el_uuid_y_no_toca_la_carpeta(make_window):
    window = make_window()
    assert window.btn_refresh_uuid.text() == "" and not window.btn_refresh_uuid.icon().isNull()
    before = window.input_filename.text()
    window.input_folder.setText("D:/musica")
    window.btn_refresh_uuid.click()
    assert window.input_filename.text() != before
    assert UUID_PATTERN.match(stem(window))
    assert window.input_folder.text() == "D:/musica"


def test_boton_refrescar_reemplaza_tambien_un_nombre_propio(make_window):
    window = make_window()
    window.input_filename.setText("mi-video.mp4")
    window.btn_refresh_uuid.click()
    assert UUID_PATTERN.match(stem(window))


def test_boton_refrescar_con_nombre_vacio(make_window):
    window = make_window()
    window.input_filename.setText("")
    window.btn_refresh_uuid.click()
    assert UUID_PATTERN.match(stem(window))


def test_el_tooltip_del_boton_sigue_el_idioma(make_window):
    window = make_window()
    assert window.btn_refresh_uuid.toolTip() == "Generate a new UUID"
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.btn_refresh_uuid.toolTip() == "Generar un UUID nuevo"
    assert window.label_folder.text() == "Carpeta"
    assert window.label_filename.text() == "Nombre de archivo"


def test_exportar_sin_nombre_avisa(make_window, media, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    window = make_window()
    window.slot_image.set_file(media[0])
    window.slot_audio.set_file(media[1])
    window.input_filename.setText("   ")
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(args[2]))
    window.btn_export.click()
    assert avisos == ["Enter the file name."]
    assert window._worker is None


# --- Aviso de archivo existente ----------------------------------------------


@pytest.mark.parametrize("button_text, expected", [("Replace", True), ("Cancel", False)])
def test_el_dialogo_de_reemplazo_devuelve_la_eleccion(
        make_window, tmp_path, monkeypatch, button_text, expected):
    from PySide6.QtWidgets import QMessageBox

    window = make_window()
    seen = {}

    def fake_exec(box):
        seen["text"] = box.text()
        seen["default"] = box.defaultButton().text()
        next(b for b in box.buttons() if b.text() == button_text).click()

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    assert window._confirm_overwrite(tmp_path / "a.mp4") is expected
    assert "will be replaced" in seen["text"] and str(tmp_path / "a.mp4") in seen["text"]
    assert seen["default"] == "Cancel"  # por defecto no reemplaza


def test_avisa_si_el_archivo_existe_y_no_lo_reemplaza_si_se_cancela(
        make_window, media, tmp_path, monkeypatch):
    window = make_window()
    window.slot_image.set_file(media[0])
    window.slot_audio.set_file(media[1])
    existing = tmp_path / "ya-existe.mp4"
    existing.write_bytes(b"original")
    window.input_folder.setText(str(tmp_path))
    window.input_filename.setText("ya-existe.mp4")

    avisos = []
    monkeypatch.setattr(window, "_confirm_overwrite", lambda path: avisos.append(path) or False)
    window.btn_export.click()

    assert avisos == [existing]
    assert window._worker is None
    assert existing.read_bytes() == b"original"


def test_reemplaza_el_archivo_si_el_usuario_confirma(
        qapp, make_window, media, tmp_path, monkeypatch):
    window = make_window()
    window.slot_image.set_file(media[0])
    window.slot_audio.set_file(media[1])
    window.combo_resolution.setCurrentIndex(0)
    existing = tmp_path / "ya-existe.mp4"
    existing.write_bytes(b"original")
    window.input_folder.setText(str(tmp_path))
    window.input_filename.setText("ya-existe.mp4")

    monkeypatch.setattr(window, "_confirm_overwrite", lambda path: True)
    window.btn_export.click()
    wait_for_worker(qapp, window)

    assert existing.read_bytes() != b"original"
    assert existing.stat().st_size > 1000


def test_no_avisa_si_el_archivo_no_existe(qapp, make_window, media, tmp_path, monkeypatch):
    window = make_window()
    window.slot_image.set_file(media[0])
    window.slot_audio.set_file(media[1])
    window.combo_resolution.setCurrentIndex(0)
    window.input_folder.setText(str(tmp_path / "nueva-carpeta"))
    window.input_filename.setText("nuevo.mp4")

    monkeypatch.setattr(window, "_confirm_overwrite",
                        lambda path: pytest.fail("no debía avisar"))
    window.btn_export.click()
    wait_for_worker(qapp, window)
    assert (tmp_path / "nueva-carpeta" / "nuevo.mp4").exists()


# --- Información del audio -----------------------------------------------------


def test_muestra_duracion_formato_bitrate_y_bit_depth(make_window, media):
    window = make_window()
    window.slot_audio.set_file(media[1])
    text = window.slot_audio.info.text()
    assert "track.wav" in text
    assert "Duration: 0:02" in text
    assert "Format: WAV" in text
    assert "Bitrate: 128 kbps" in text  # 8000 Hz x 16 bits x 1 canal
    assert "Bit depth: 16-bit" in text


def test_la_informacion_del_audio_sigue_el_idioma(make_window, media):
    window = make_window()
    window.slot_audio.set_file(media[1])
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    text = window.slot_audio.info.text()
    assert "Duración: 0:02" in text and "Formato: WAV" in text
    assert "Profundidad de bits: 16-bit" in text


def test_un_audio_con_perdida_no_tiene_bit_depth(make_window, tmp_path):
    wav, mp3 = tmp_path / "a.wav", tmp_path / "a.mp3"
    make_wav(wav, rate=44100)
    result = subprocess.run([get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(wav),
                             "-b:a", "128k", str(mp3)], capture_output=True)
    if result.returncode != 0:
        pytest.skip("este FFmpeg no incluye libmp3lame")
    window = make_window()
    window.slot_audio.set_file(str(mp3))
    text = window.slot_audio.info.text()
    assert "Format: MP3" in text and "Bit depth: —" in text
    assert "Bitrate: 128 kbps" in text


# --- Vista previa del audio ----------------------------------------------------


class FakePlayer:
    """Reemplaza al QMediaPlayer para probar el botón sin dispositivo de audio."""

    def __init__(self):
        self.state = QMediaPlayer.StoppedState
        self.calls = []

    def play(self):
        self.state = QMediaPlayer.PlayingState
        self.calls.append("play")

    def stop(self):
        self.state = QMediaPlayer.StoppedState
        self.calls.append("stop")

    def playbackState(self):
        return self.state

    def setSource(self, url):
        self.calls.append(("source", url.toLocalFile()))


def test_el_boton_de_preview_aparece_solo_con_audio(qapp, make_window, media):
    window = make_window()
    window.show()
    slot = window.slot_audio
    assert not slot.btn_play.isVisible()
    slot.set_file(media[1])
    assert slot.btn_play.isVisible()
    assert slot.btn_play.text() == "Play" and not slot.btn_play.icon().isNull()
    slot.clear()
    assert not slot.btn_play.isVisible()


def test_el_audio_se_carga_en_el_reproductor(make_window, media):
    slot = make_window().slot_audio
    slot.set_file(media[1])
    assert Path(slot.player.source().toLocalFile()) == Path(media[1])
    slot.clear()
    assert slot.player.source().isEmpty()


def test_el_boton_reproduce_y_detiene(make_window, media):
    slot = make_window().slot_audio
    slot.set_file(media[1])
    slot.player = fake = FakePlayer()

    slot.btn_play.click()
    slot._update_play_button()  # en la app lo dispara la señal del reproductor
    assert fake.calls == ["play"]
    assert slot.btn_play.text() == "Stop"

    slot.btn_play.click()
    slot._update_play_button()
    assert fake.calls == ["play", "stop"]
    assert slot.btn_play.text() == "Play"


def test_cambiar_o_quitar_el_audio_detiene_la_vista_previa(make_window, media, tmp_path):
    slot = make_window().slot_audio
    slot.set_file(media[1])
    slot.player = fake = FakePlayer()
    slot.btn_play.click()

    other = tmp_path / "otro.wav"
    make_wav(other)
    slot.set_file(str(other))
    assert fake.calls[:2] == ["play", "stop"]
    assert fake.calls[2] == ("source", str(other).replace("\\", "/"))

    slot.clear()
    assert fake.calls[-2:] == ["stop", ("source", "")]


def test_el_texto_del_boton_de_preview_sigue_el_idioma(make_window, media):
    window = make_window()
    window.slot_audio.set_file(media[1])
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.slot_audio.btn_play.text() == "Reproducir"
    window.slot_audio.player = FakePlayer()
    window.slot_audio.btn_play.click()
    window.slot_audio._update_play_button()
    assert window.slot_audio.btn_play.text() == "Detener"


# --- Tema ------------------------------------------------------------------------


def test_el_tema_por_defecto_es_sistema_y_es_la_primera_opcion(make_window):
    window = make_window()
    combo = window.combo_theme
    assert [combo.itemData(i) for i in range(combo.count())] == ["system", "light", "dark"]
    assert [combo.itemText(i) for i in range(combo.count())] == ["System", "Light", "Dark"]
    assert combo.currentData() == "system"


@pytest.fixture
def applied_themes(monkeypatch):
    """Registra los temas que la ventana pide aplicar (la plataforma offscreen no los aplica)."""
    from tracktube.ui import main_window

    applied = []
    monkeypatch.setattr(main_window, "apply_theme", applied.append)
    return applied


def test_cambiar_el_tema_pide_aplicar_claro_oscuro_y_sistema(make_window, applied_themes):
    window = make_window()
    for theme in ("dark", "light", "system"):
        window.combo_theme.setCurrentIndex(window.combo_theme.findData(theme))
    assert applied_themes == ["dark", "light", "system"]


def test_el_tema_se_guarda_y_se_aplica_al_abrir(make_window, applied_themes):
    window = make_window()
    window.combo_theme.setCurrentIndex(window.combo_theme.findData("dark"))
    window.close()
    applied_themes.clear()

    other = make_window()
    assert other.combo_theme.currentData() == "dark"
    assert applied_themes == ["dark"]


def test_el_icono_de_orientacion_se_redibuja_al_cambiar_la_paleta(make_window):
    from PySide6.QtGui import QColor, QPalette

    window = make_window()
    window.show()

    def icon_color():
        image = window.btn_vertical.icon().pixmap(24, 24).toImage()
        return image.pixelColor(7, 10)  # sobre el borde izquierdo del rectángulo

    palette = window.palette()
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    window.setPalette(palette)
    assert icon_color().red() > 200
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    window.setPalette(palette)
    assert icon_color().red() < 50


def test_el_selector_de_tema_sigue_el_idioma(make_window):
    window = make_window()
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    combo = window.combo_theme
    assert [combo.itemText(i) for i in range(combo.count())] == ["Sistema", "Claro", "Oscuro"]
    assert window.label_theme.text() == "Tema:"
