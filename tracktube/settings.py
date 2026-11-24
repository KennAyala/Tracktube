from PySide6.QtCore import QSettings

from tracktube.config import SETTINGS_PATH


def create_settings(path=SETTINGS_PATH):
    """Configuración del usuario en un archivo .ini; crea la carpeta si no existe."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return QSettings(str(path), QSettings.IniFormat)
