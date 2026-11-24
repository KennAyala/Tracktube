import time
import uuid
import wave
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QSettings

from tracktube.ui.main_window import UUID_PATTERN


def new_uuid_name():
    return f"{uuid.uuid4()}.mp4"


def save_export_path(settings_file, text):
    settings = QSettings(settings_file, QSettings.IniFormat)
    settings.setValue("export_path", text)
    settings.sync()


def stem(window):
    return Path(window.input_path.text()).stem


@pytest.fixture
def media(tmp_path):
    image = tmp_path / "cover.png"
    Image.new("RGB", (200, 200), (10, 100, 200)).save(image)
    audio = tmp_path / "track.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * 8000 * 2)
    return str(image), str(audio)


def wait_for_worker(qapp, window, timeout=60):
    deadline = time.monotonic() + timeout
    while window._worker is not None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()
    assert window._worker is None, "la exportación no terminó"


# --- UUID ------------------------------------------------------------------


def test_por_defecto_la_ruta_es_exports_uuid(make_window):
    window = make_window()
    assert window.input_path.text().startswith("exports/")
    assert UUID_PATTERN.match(stem(window))


def test_el_uuid_cambia_cada_vez_que_se_abre_la_app(make_window, settings_file):
    old_name = new_uuid_name()
    save_export_path(settings_file, f"D:/musica/{old_name}")
    window = make_window()
    path = Path(window.input_path.text())
    assert path.name != old_name and UUID_PATTERN.match(path.stem)
    assert path.parent == Path("D:/musica")  # conserva la carpeta


def test_nombre_propio_se_respeta_al_abrir(make_window, settings_file):
    save_export_path(settings_file, "D:/musica/mi-video.mp4")
    assert Path(make_window().input_path.text()) == Path("D:/musica/mi-video.mp4")


def test_el_uuid_cambia_al_terminar_la_exportacion(make_window, tmp_path):
    window = make_window()
    original = window.input_path.text()
    window._output = tmp_path / "x.mp4"
    window._on_export_succeeded()
    assert window.input_path.text() != original
    assert UUID_PATTERN.match(stem(window))


def test_nombre_propio_se_respeta_al_terminar(make_window, tmp_path):
    window = make_window()
    window.input_path.setText("D:/musica/mi-video.mp4")
    window._output = tmp_path / "x.mp4"
    window._on_export_succeeded()
    assert Path(window.input_path.text()) == Path("D:/musica/mi-video.mp4")


def test_boton_refrescar_cambia_el_uuid(make_window):
    window = make_window()
    assert window.btn_refresh_uuid.text() == "" and not window.btn_refresh_uuid.icon().isNull()
    before = window.input_path.text()
    window.btn_refresh_uuid.click()
    assert window.input_path.text() != before
    assert UUID_PATTERN.match(stem(window))
    assert window.input_path.text().startswith("exports")


def test_boton_refrescar_reemplaza_tambien_un_nombre_propio(make_window):
    window = make_window()
    window.input_path.setText("D:/musica/mi-video.mp4")
    window.btn_refresh_uuid.click()
    path = Path(window.input_path.text())
    assert UUID_PATTERN.match(path.stem) and path.parent == Path("D:/musica")


def test_boton_refrescar_con_ruta_vacia(make_window):
    window = make_window()
    window.input_path.setText("")
    window.btn_refresh_uuid.click()
    assert UUID_PATTERN.match(stem(window))


def test_el_tooltip_del_boton_sigue_el_idioma(make_window):
    window = make_window()
    assert window.btn_refresh_uuid.toolTip() == "Generate a new UUID"
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.btn_refresh_uuid.toolTip() == "Generar un UUID nuevo"


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
    window.input_path.setText(str(existing))

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
    window.input_path.setText(str(existing))

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
    window.input_path.setText(str(tmp_path / "nuevo.mp4"))

    monkeypatch.setattr(window, "_confirm_overwrite",
                        lambda path: pytest.fail("no debía avisar"))
    window.btn_export.click()
    wait_for_worker(qapp, window)
    assert (tmp_path / "nuevo.mp4").exists()
