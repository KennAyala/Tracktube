from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
)


class FileSlot(QGroupBox):
    """Input para un archivo: agregar, reemplazar, eliminar y arrastrar y soltar.

    `loader(path)` valida el archivo y devuelve (texto_info, QPixmap | None);
    si el archivo no es válido debe lanzar ValueError.
    """

    changed = Signal()

    def __init__(self, title, extensions, loader, parent=None):
        super().__init__(title, parent)
        self.extensions = extensions
        self.loader = loader
        self.path = None
        self.setAcceptDrops(True)

        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(72, 72)
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.hide()

        self.info = QLabel("Ningún archivo seleccionado")
        self.info.setWordWrap(True)

        self.btn_choose = QPushButton("Agregar")
        self.btn_remove = QPushButton("Eliminar")
        self.btn_remove.hide()
        self.btn_choose.clicked.connect(self._choose)
        self.btn_remove.clicked.connect(self.clear)

        buttons = QVBoxLayout()
        buttons.addWidget(self.btn_choose)
        buttons.addWidget(self.btn_remove)

        layout = QHBoxLayout(self)
        layout.addWidget(self.thumbnail)
        layout.addWidget(self.info, 1)
        layout.addLayout(buttons)

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
        self.info.setText(f"{Path(path).name}\n{info}")
        if pixmap is not None:
            self.thumbnail.setPixmap(pixmap.scaled(
                self.thumbnail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.thumbnail.show()
        self.btn_choose.setText("Reemplazar")
        self.btn_remove.show()
        self.changed.emit()

    def clear(self):
        self.path = None
        self.info.setText("Ningún archivo seleccionado")
        self.thumbnail.hide()
        self.btn_choose.setText("Agregar")
        self.btn_remove.hide()
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
