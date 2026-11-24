from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton

from tracktube.i18n import tr
from tracktube.ui.file_slot import FileSlot


class ImageSlot(FileSlot):
    """FileSlot de imagen con un botón para usar la imagen incrustada en los tags del audio."""

    metadata_cover_requested = Signal()

    def __init__(self, title_key, extensions, loader, parent=None):
        super().__init__(title_key, extensions, loader, parent)
        self.btn_metadata = QPushButton()
        self.btn_metadata.hide()  # solo aparece cuando el audio trae una imagen en sus tags
        self.btn_metadata.clicked.connect(self.metadata_cover_requested)
        self.buttons_layout.addWidget(self.btn_metadata)
        self.retranslate()

    def set_metadata_cover_available(self, available):
        self.btn_metadata.setVisible(available)

    def retranslate(self):
        super().retranslate()
        if hasattr(self, "btn_metadata"):  # se llama también desde el constructor de FileSlot
            self.btn_metadata.setText(tr("cover.use_metadata"))
            self.btn_metadata.setToolTip(tr("cover.use_metadata_tip"))
