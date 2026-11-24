from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
)

from tracktube.i18n import tr


class FileSlot(QGroupBox):
    """Input para un archivo: agregar, reemplazar, eliminar y arrastrar y soltar.

    `loader(path)` valida el archivo y devuelve ((clave_i18n, parámetros), QPixmap | None);
    si el archivo no es válido debe lanzar ValueError.
    """

    changed = Signal()

    def __init__(self, title_key, extensions, loader, parent=None):
        super().__init__(parent)
        self.title_key = title_key
        self.extensions = extensions
        self.loader = loader
        self.path = None
        self._info = None
        self.setAcceptDrops(True)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(72, 72)
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.hide()

        self.info = QLabel()
        self.info.setWordWrap(True)

        self.btn_choose = QPushButton()
        self.btn_remove = QPushButton()
        self.btn_remove.hide()
        self.btn_choose.clicked.connect(self._choose)
        self.btn_remove.clicked.connect(self.clear)

        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.addWidget(self.btn_choose)
        self.buttons_layout.addWidget(self.btn_remove)

        layout = QHBoxLayout(self)
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.info, 1)
        layout.addLayout(self.buttons_layout)
        self.retranslate()

    def retranslate(self):
        self.setTitle(tr(self.title_key))
        self.btn_choose.setText(tr("slot.replace" if self.path else "slot.add"))
        self.btn_remove.setText(tr("slot.remove"))
        if self.path is None:
            self.info.setText(tr("slot.empty"))
        else:
            self.info.setText(f"{Path(self.path).name}\n{tr(self._info[0], **self._info[1])}")

    def _choose(self):
        patterns = " ".join(f"*{ext}" for ext in self.extensions)
        path, _ = QFileDialog.getOpenFileName(
            self, self.title(), "", f"{self.title()} ({patterns})")
        if path:
            self.set_file(path)

    def set_file(self, path):
        try:
            info, pixmap = self.loader(path)
        except ValueError as e:
            QMessageBox.warning(self, self.title(), str(e))
            return
        self.path = path
        self._info = info
        if pixmap is not None:
            self.thumbnail.setPixmap(pixmap.scaled(
                self.thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.thumbnail.show()
        self.btn_remove.show()
        self.retranslate()
        self.changed.emit()

    def clear(self):
        self.path = None
        self._info = None
        self.thumbnail.hide()
        self.btn_remove.hide()
        self.retranslate()
        self.changed.emit()

    def dragEnterEvent(self, event):
        if self._dropped_path(event) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = self._dropped_path(event)
        if path is not None:
            self.set_file(path)

    def _dropped_path(self, event):
        urls = event.mimeData().urls()
        if not urls or not urls[0].isLocalFile():
            return None
        path = urls[0].toLocalFile()
        return path if Path(path).suffix.lower() in self.extensions else None
