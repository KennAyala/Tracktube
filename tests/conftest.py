import os

# Las pruebas de UI corren sin pantalla
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from tracktube import i18n


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def settings_file(tmp_path):
    return str(tmp_path / "settings.ini")


@pytest.fixture
def make_window(qapp, settings_file, monkeypatch):
    """Crea ventanas con una configuración temporal y sin diálogos modales."""
    from tracktube.ui.main_window import MainWindow

    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    windows = []

    def factory():
        window = MainWindow(QSettings(settings_file, QSettings.IniFormat))
        windows.append(window)
        return window

    yield factory
    for window in windows:
        window.close()
        window.log_panel.detach()
    i18n.set_language("en")
