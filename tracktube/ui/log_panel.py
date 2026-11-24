import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QPlainTextEdit

from tracktube.log import logger

MAX_LINES = 5000


class _LogEmitter(QObject):
    message = Signal(str)


class QtLogHandler(logging.Handler):
    """Reenvía los registros por una señal de Qt, así es seguro usarlo desde hilos."""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.emitter = _LogEmitter()
        self.setFormatter(logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", "%H:%M:%S"))

    def emit(self, record):
        self.emitter.message.emit(self.format(record))


class LogPanel(QPlainTextEdit):
    """Muestra el log de depuración de la app."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(MAX_LINES)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.setMinimumWidth(420)

        self._handler = QtLogHandler()
        self._handler.emitter.message.connect(self.appendPlainText)
        logger.addHandler(self._handler)

    def detach(self):
        logger.removeHandler(self._handler)
