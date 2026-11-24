from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout

from tracktube.core.fit_modes import DEFAULT_BACKGROUND, DEFAULT_FIT_MODE, render_preview
from tracktube.i18n import tr

PREVIEW_BOX = 400


def pil_to_pixmap(image):
    """Convierte una imagen PIL a QPixmap conservando la transparencia."""
    image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


class PreviewWidget(QGroupBox):
    """Muestra cómo se verá el frame que ocupará todo el video."""

    export_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = None
        self._ratio = (16, 9)
        self._mode = DEFAULT_FIT_MODE
        self._background = DEFAULT_BACKGROUND
        self._shadow = False
        self._margin = 0
        self._background_image = None

        self.canvas = QLabel()
        self.canvas.setFixedSize(PREVIEW_BOX, PREVIEW_BOX)
        self.canvas.setAlignment(Qt.AlignCenter)

        self.btn_export_image = QPushButton()
        self.btn_export_image.setEnabled(False)  # necesita una imagen cargada
        self.btn_export_image.clicked.connect(self.export_requested)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        layout.addWidget(self.btn_export_image)
        self.retranslate()

    def retranslate(self):
        self.setTitle(tr("preview.title"))
        self.btn_export_image.setText(tr("preview.export_image"))
        self.btn_export_image.setToolTip(tr("preview.export_image_tip"))
        self._refresh()

    def set_image(self, image):
        self._image = image
        self.btn_export_image.setEnabled(image is not None)
        self._refresh()

    def set_ratio(self, ratio_w, ratio_h):
        self._ratio = (ratio_w, ratio_h)
        self._refresh()

    def set_options(self, mode, background, shadow, margin, background_image):
        self._mode = mode
        self._background = background
        self._shadow = shadow
        self._margin = margin
        self._background_image = background_image
        self._refresh()

    def _refresh(self):
        ratio_w, ratio_h = self._ratio
        scale = PREVIEW_BOX / max(ratio_w, ratio_h)
        width, height = round(ratio_w * scale), round(ratio_h * scale)

        if self._image is None:
            pixmap = QPixmap(width, height)
            pixmap.fill(QColor(40, 40, 40))
            painter = QPainter(pixmap)
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, tr("preview.empty"))
            painter.end()
        else:
            pixmap = pil_to_pixmap(render_preview(
                self._image, self._mode, width, height, self._background,
                self._shadow, self._margin, self._background_image))
        self.canvas.setPixmap(pixmap)
