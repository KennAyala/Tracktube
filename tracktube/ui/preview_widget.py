from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from tracktube.config import LABEL_IMAGE
from tracktube.core.fit_modes import render_preview

PREVIEW_BOX = 400


def pil_to_pixmap(image):
    image = image.convert("RGB")
    data = image.tobytes("raw", "RGB")
    qimage = QImage(data, image.width, image.height, image.width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


class PreviewWidget(QGroupBox):
    """Muestra cómo se verá el frame que ocupará todo el video."""

    def __init__(self, parent=None):
        super().__init__("Preview", parent)
        self._image = None
        self._ratio = (16, 9)
        self._mode = "ajustar"

        self.canvas = QLabel()
        self.canvas.setFixedSize(PREVIEW_BOX, PREVIEW_BOX)
        self.canvas.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self._refresh()

    def set_image(self, image):
        self._image = image
        self._refresh()

    def set_ratio(self, ratio_w, ratio_h):
        self._ratio = (ratio_w, ratio_h)
        self._refresh()

    def set_mode(self, mode):
        self._mode = mode
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
            painter.drawText(pixmap.rect(), Qt.AlignCenter, f"Sin {LABEL_IMAGE}")
            painter.end()
        else:
            pixmap = pil_to_pixmap(render_preview(self._image, self._mode, width, height))
        self.canvas.setPixmap(pixmap)
