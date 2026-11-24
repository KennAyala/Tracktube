from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from tracktube.ui.theme import DEFAULT_THEME, THEMES, apply_theme


class FakeStyleHints:
    def __init__(self):
        self.schemes = []

    def setColorScheme(self, scheme):
        self.schemes.append(scheme)


def fake_hints(monkeypatch):
    hints = FakeStyleHints()
    monkeypatch.setattr(QGuiApplication, "styleHints", staticmethod(lambda: hints))
    return hints


def test_sistema_es_el_tema_por_defecto_y_va_primero():
    assert DEFAULT_THEME == "system"
    assert THEMES == ("system", "light", "dark")


def test_cada_tema_pide_su_esquema_de_color(monkeypatch):
    hints = fake_hints(monkeypatch)
    for theme in THEMES:
        apply_theme(theme)
    assert hints.schemes == [
        Qt.ColorScheme.Unknown,  # sistema: Qt sigue la configuración de Windows
        Qt.ColorScheme.Light,
        Qt.ColorScheme.Dark,
    ]


def test_un_tema_desconocido_vuelve_al_sistema(monkeypatch):
    hints = fake_hints(monkeypatch)
    apply_theme("otro")
    assert hints.schemes == [Qt.ColorScheme.Unknown]
