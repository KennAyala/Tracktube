"""UI: imagen de metadatos del audio y exportar la vista previa como imagen."""
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtWidgets import QFileDialog, QMessageBox

from audio_helpers import embed_cover, image_bytes, make_audio, make_wav
from test_main_window import wait_for_worker
from tracktube.core.image_export import IMAGE_FILTERS, JPG_FILTER, PNG_FILTER


@pytest.fixture
def media(tmp_path):
    image = tmp_path / "cover.png"
    Image.new("RGB", (200, 200), (10, 100, 200)).save(image)
    audio = make_wav(tmp_path / "track.wav")
    return str(image), str(audio)


@pytest.fixture
def audio_with_cover(tmp_path):
    path = make_audio(tmp_path, "mp3", "con-caratula")
    embed_cover(path, "mp3", image_bytes("PNG", (300, 300), (10, 200, 30)), "image/png")
    return str(path)


def test_el_audio_va_antes_que_la_imagen(qapp, make_window):
    window = make_window()
    window.show()
    qapp.processEvents()
    assert window.slot_audio.geometry().bottom() < window.slot_image.geometry().top()
    assert window.slot_image.geometry().bottom() < window.group_settings.geometry().top()


# --- Imagen de metadatos --------------------------------------------------------


def test_el_boton_de_metadatos_aparece_solo_si_el_audio_trae_imagen(
        make_window, media, audio_with_cover):
    window = make_window()
    window.show()
    button = window.slot_image.btn_metadata
    assert not button.isVisible()

    window.slot_audio.set_file(audio_with_cover)
    assert button.isVisible()
    assert button.text() == "Use metadata image"

    window.slot_audio.set_file(media[1])  # audio sin imagen en los tags
    assert not button.isVisible()

    window.slot_audio.set_file(audio_with_cover)
    assert button.isVisible()
    window.slot_audio.clear()
    assert not button.isVisible()


def test_cargar_el_audio_no_cambia_la_imagen_por_si_solo(make_window, audio_with_cover):
    window = make_window()
    window.slot_audio.set_file(audio_with_cover)
    assert window.slot_image.path is None and window._image is None


def test_el_boton_usa_la_imagen_de_los_metadatos_como_album_art(make_window, audio_with_cover):
    window = make_window()
    window.slot_audio.set_file(audio_with_cover)
    window.slot_image.btn_metadata.click()

    path = Path(window.slot_image.path)
    assert path.name == "metadata-cover.png" and path.is_file()
    assert window._image.size == (300, 300)
    assert "300 × 300 px" in window.slot_image.info.text()
    assert window.preview.btn_export_image.isEnabled()
    assert window.slot_image.btn_metadata.isEnabled()  # sigue disponible para volver a usarla


def test_se_puede_volver_a_la_imagen_de_metadatos_tras_reemplazarla(
        make_window, audio_with_cover, media):
    window = make_window()
    window.slot_audio.set_file(audio_with_cover)
    window.slot_image.set_file(media[0])
    assert Path(window.slot_image.path).name == "cover.png"
    window.slot_image.btn_metadata.click()
    assert Path(window.slot_image.path).name == "metadata-cover.png"


def test_la_imagen_de_metadatos_se_borra_al_cerrar_la_app(make_window, audio_with_cover):
    window = make_window()
    window.slot_audio.set_file(audio_with_cover)
    window.slot_image.btn_metadata.click()
    folder = Path(window._temp_dir.name)
    assert folder.is_dir()
    window.close()
    assert not folder.exists()


def test_el_boton_de_metadatos_sigue_el_idioma(make_window, audio_with_cover):
    window = make_window()
    window.slot_audio.set_file(audio_with_cover)
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.slot_image.btn_metadata.text() == "Utilizar imagen de metadatos"


def test_una_imagen_incrustada_corrupta_avisa_y_no_cambia_la_imagen(
        make_window, tmp_path, monkeypatch):
    path = make_audio(tmp_path, "mp3", "corrupta")
    embed_cover(path, "mp3", b"esto no es una imagen", "image/png")
    window = make_window()
    window.slot_audio.set_file(str(path))
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(args[2]))
    window.slot_image.btn_metadata.click()
    assert len(avisos) == 1
    assert window.slot_image.path is None


def test_exportar_con_la_imagen_de_metadatos(qapp, make_window, audio_with_cover, tmp_path):
    window = make_window()
    window.slot_audio.set_file(audio_with_cover)
    window.slot_image.btn_metadata.click()
    window.combo_resolution.setCurrentIndex(0)
    window.input_folder.setText(str(tmp_path))
    window.input_filename.setText("con-metadatos.mp4")
    window.btn_export.click()
    wait_for_worker(qapp, window)
    assert (tmp_path / "con-metadatos.mp4").stat().st_size > 1000


# --- Exportar la vista previa como imagen -----------------------------------------


@pytest.fixture
def save_dialog(monkeypatch):
    """Sustituye el diálogo de guardar; devuelve lo que recibió y permite elegir la respuesta."""
    state = {"answer": ("", ""), "calls": []}

    def fake(parent, title, start, filters, *args):
        state["calls"].append({"title": title, "start": start, "filters": filters})
        return state["answer"]

    monkeypatch.setattr(QFileDialog, "getSaveFileName", fake)
    return state


def test_el_boton_de_exportar_la_vista_previa_necesita_una_imagen(make_window, media):
    window = make_window()
    button = window.preview.btn_export_image
    assert button.text() == "Export preview as image" and not button.isEnabled()
    window.slot_image.set_file(media[0])
    assert button.isEnabled()
    window.slot_image.clear()
    assert not button.isEnabled()


def test_el_boton_de_exportar_la_vista_previa_sigue_el_idioma(make_window):
    window = make_window()
    window.combo_language.setCurrentIndex(window.combo_language.findData("es"))
    assert window.preview.btn_export_image.text() == "Exportar vista previa como imagen"


def test_exporta_la_vista_previa_como_jpg_por_defecto(make_window, media, save_dialog, tmp_path):
    window = make_window()
    window.slot_image.set_file(media[0])
    window.slot_audio.set_file(media[1])
    window.input_folder.setText(str(tmp_path))
    save_dialog["answer"] = (str(tmp_path / "vista"), JPG_FILTER)
    window.preview.btn_export_image.click()

    call = save_dialog["calls"][0]
    assert call["filters"] == IMAGE_FILTERS and call["filters"].startswith("JPG")
    assert Path(call["start"]) == tmp_path / "track.jpg"  # nombre del audio, JPG por defecto
    with Image.open(tmp_path / "vista.jpg") as image:
        assert image.format == "JPEG" and image.size == (1920, 1080)


def test_exporta_la_vista_previa_como_png(make_window, media, save_dialog, tmp_path):
    window = make_window()
    window.slot_image.set_file(media[0])
    save_dialog["answer"] = (str(tmp_path / "vista"), PNG_FILTER)
    window.preview.btn_export_image.click()
    with Image.open(tmp_path / "vista.png") as image:
        assert image.format == "PNG" and image.size == (1920, 1080)


def test_la_extension_escrita_manda_sobre_el_filtro(make_window, media, save_dialog, tmp_path):
    window = make_window()
    window.slot_image.set_file(media[0])
    save_dialog["answer"] = (str(tmp_path / "vista.png"), JPG_FILTER)
    window.preview.btn_export_image.click()
    assert (tmp_path / "vista.png").is_file() and not (tmp_path / "vista.png.jpg").exists()


def test_sin_audio_el_nombre_sugerido_es_preview(make_window, media, save_dialog):
    window = make_window()
    window.slot_image.set_file(media[0])
    window.preview.btn_export_image.click()  # el diálogo se cancela (respuesta vacía)
    assert Path(save_dialog["calls"][0]["start"]).name == "preview.jpg"


def test_cancelar_el_dialogo_no_guarda_nada(make_window, media, save_dialog, tmp_path):
    window = make_window()
    window.slot_image.set_file(media[0])
    save_dialog["answer"] = ("", "")
    window.preview.btn_export_image.click()
    assert list(tmp_path.glob("*.jpg")) == [] and list(tmp_path.glob("vista*")) == []


def test_la_imagen_exportada_usa_la_resolucion_y_el_ratio_elegidos(
        make_window, media, save_dialog, tmp_path):
    window = make_window()
    window.slot_image.set_file(media[0])
    window.btn_vertical.click()  # 16:9 -> 9:16
    window.combo_resolution.setCurrentIndex(0)  # 480p
    save_dialog["answer"] = (str(tmp_path / "vertical.png"), PNG_FILTER)
    window.preview.btn_export_image.click()
    with Image.open(tmp_path / "vertical.png") as image:
        assert image.size == (480, 854)


def test_la_imagen_exportada_usa_los_ajustes_de_la_vista_previa(
        make_window, media, save_dialog, tmp_path):
    window = make_window()
    window.slot_image.set_file(media[0])  # cuadrada, azul (10, 100, 200)
    window.combo_ratio.setCurrentIndex(0)  # 1:1
    window.combo_resolution.setCurrentIndex(0)
    save_dialog["answer"] = (str(tmp_path / "sin-margen.png"), PNG_FILTER)
    window.preview.btn_export_image.click()
    window.spin_margin.setValue(20)
    save_dialog["answer"] = (str(tmp_path / "con-margen.png"), PNG_FILTER)
    window.preview.btn_export_image.click()

    with Image.open(tmp_path / "sin-margen.png") as plain, \
            Image.open(tmp_path / "con-margen.png") as framed:
        assert plain.getpixel((5, 5)) == (10, 100, 200)  # la imagen llena el cuadro
        assert framed.getpixel((5, 5)) == (0, 0, 0)      # el margen la aleja del borde
        assert framed.getpixel((240, 240)) == (10, 100, 200)


def test_un_error_al_guardar_la_imagen_se_avisa(make_window, media, save_dialog, tmp_path,
                                                monkeypatch):
    from tracktube.ui import main_window

    def fail(image, path):
        raise OSError("disco lleno")

    monkeypatch.setattr(main_window, "save_image", fail)
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: avisos.append(args[2]))
    window = make_window()
    window.slot_image.set_file(media[0])
    save_dialog["answer"] = (str(tmp_path / "x.jpg"), JPG_FILTER)
    window.preview.btn_export_image.click()
    assert avisos == ["Could not save the image:\ndisco lleno"]
