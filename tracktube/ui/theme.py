from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

# "system" sigue la configuración de claro/oscuro de Windows
THEMES = ("system", "light", "dark")
DEFAULT_THEME = "system"

_COLOR_SCHEMES = {
    "system": Qt.ColorScheme.Unknown,
    "light": Qt.ColorScheme.Light,
    "dark": Qt.ColorScheme.Dark,
}


def apply_theme(theme):
    QGuiApplication.styleHints().setColorScheme(
        _COLOR_SCHEMES.get(theme, Qt.ColorScheme.Unknown))
