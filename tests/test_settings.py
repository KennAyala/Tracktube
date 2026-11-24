from pathlib import Path

import shiboken6

from tracktube.config import BASE_DIR, SETTINGS_PATH
from tracktube.settings import create_settings


def test_la_configuracion_va_en_user_conf_ini():
    assert SETTINGS_PATH == BASE_DIR / "user" / "conf.ini"


def test_crea_la_carpeta_y_guarda_en_formato_ini(tmp_path):
    path = tmp_path / "user" / "conf.ini"
    settings = create_settings(path)
    assert path.parent.is_dir()
    settings.setValue("theme", "dark")
    settings.setValue("export_folder", "D:/musica")
    settings.sync()
    content = path.read_text(encoding="utf-8")
    assert "theme=dark" in content
    assert "export_folder" in content


def test_lee_lo_guardado_en_otra_instancia(tmp_path):
    path = tmp_path / "user" / "conf.ini"
    create_settings(path).setValue("language", "es")
    create_settings(path).sync()
    assert create_settings(path).value("language", "en", type=str) == "es"


def test_la_ventana_usa_la_configuracion_de_user(qapp, tmp_path, monkeypatch):
    from tracktube.ui import main_window

    path = tmp_path / "user" / "conf.ini"
    monkeypatch.setattr(main_window, "create_settings", lambda: create_settings(path))
    window = main_window.MainWindow()
    try:
        window.input_filename.setText("mi-video.mp4")
        window.close()
        assert path.is_file()
        assert "mi-video.mp4" in path.read_text(encoding="utf-8")
    finally:
        window.log_panel.detach()
        shiboken6.delete(window)  # se destruye aquí, en el hilo principal


def test_la_carpeta_user_esta_en_el_gitignore():
    lines = (BASE_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "user/" in [line.strip() for line in lines]
    assert isinstance(SETTINGS_PATH, Path)
