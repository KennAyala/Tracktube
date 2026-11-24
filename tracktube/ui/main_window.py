import os
import uuid
from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QRadioButton,
    QVBoxLayout, QWidget,
)

from tracktube.config import (
    APP_NAME, AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, LABEL_AUDIO, LABEL_IMAGE,
)
from tracktube.core import export_path, media_info, presets
from tracktube.core.fit_modes import DEFAULT_FIT_MODE, FIT_MODES
from tracktube.ui.export_worker import ExportWorker
from tracktube.ui.file_slot import FileSlot
from tracktube.ui.preview_widget import PreviewWidget, pil_to_pixmap


def format_duration(seconds):
    minutes, secs = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self._image = None
        self._duration = 0
        self._worker = None

        self.slot_image = FileSlot(LABEL_IMAGE, IMAGE_EXTENSIONS, self._load_image)
        self.slot_audio = FileSlot(LABEL_AUDIO, AUDIO_EXTENSIONS, self._load_audio)
        self.slot_image.changed.connect(self._on_image_changed)
        self.slot_audio.changed.connect(self._on_audio_changed)

        self.preview = PreviewWidget()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        left = QVBoxLayout()
        left.addWidget(self.slot_image)
        left.addWidget(self.slot_audio)
        left.addWidget(self._build_settings())
        left.addWidget(self._build_export())
        left.addStretch(1)
        layout.addLayout(left, 1)
        layout.addWidget(self.preview)

        self._update_dimensions()
        self._update_export_enabled()

    # --- construcción de la UI -------------------------------------------------

    def _build_settings(self):
        box = QGroupBox("Ajustes")
        grid = QGridLayout(box)

        self.combo_ratio = QComboBox()
        self.combo_ratio.addItems(presets.ASPECT_RATIOS)
        self.combo_ratio.setCurrentText(presets.DEFAULT_ASPECT_RATIO)

        self.combo_resolution = QComboBox()
        for short_side in presets.RESOLUTIONS:
            self.combo_resolution.addItem(f"{short_side}p", short_side)
        self.combo_resolution.setCurrentIndex(
            self.combo_resolution.findData(presets.DEFAULT_RESOLUTION))

        self.combo_fit = QComboBox()
        for key, label in FIT_MODES.items():
            self.combo_fit.addItem(label, key)
        self.combo_fit.setCurrentIndex(self.combo_fit.findData(DEFAULT_FIT_MODE))

        self.label_dimensions = QLabel()

        self.fps_group = QButtonGroup(self)
        fps_layout = QHBoxLayout()
        for fps in presets.FPS_OPTIONS:
            text = f"Mínimo ({fps} fps)" if fps == presets.MIN_FPS else str(fps)
            radio = QRadioButton(text)
            radio.setChecked(fps == presets.DEFAULT_FPS)
            self.fps_group.addButton(radio, fps)
            fps_layout.addWidget(radio)
        fps_layout.addStretch(1)

        grid.addWidget(QLabel("Aspect ratio"), 0, 0)
        grid.addWidget(self.combo_ratio, 0, 1)
        grid.addWidget(QLabel("Resolución"), 1, 0)
        grid.addWidget(self.combo_resolution, 1, 1)
        grid.addWidget(self.label_dimensions, 1, 2)
        grid.addWidget(QLabel("Ajuste de imagen"), 2, 0)
        grid.addWidget(self.combo_fit, 2, 1, 1, 2)
        grid.addWidget(QLabel("FPS"), 3, 0)
        grid.addLayout(fps_layout, 3, 1, 1, 2)

        self.combo_ratio.currentTextChanged.connect(self._on_ratio_changed)
        self.combo_resolution.currentIndexChanged.connect(self._update_dimensions)
        self.combo_fit.currentIndexChanged.connect(
            lambda: self.preview.set_mode(self.combo_fit.currentData()))
        return box

    def _build_export(self):
        box = QGroupBox("Exportar")
        layout = QVBoxLayout(box)

        self.input_path = QLineEdit(export_path.new_default_path())
        self.btn_folder = QPushButton("Cambiar carpeta")
        self.btn_folder.clicked.connect(self._change_folder)
        path_row = QHBoxLayout()
        path_row.addWidget(self.input_path, 1)
        path_row.addWidget(self.btn_folder)
        self._generated_name = Path(self.input_path.text()).name

        self.btn_export = QPushButton("Exportar")
        self.btn_export.clicked.connect(self._start_export)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self._cancel_export)
        self.btn_cancel.hide()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        action_row = QHBoxLayout()
        action_row.addWidget(self.btn_export)
        action_row.addWidget(self.btn_cancel)
        action_row.addWidget(self.progress, 1)

        layout.addWidget(QLabel("Ruta de exportación"))
        layout.addLayout(path_row)
        layout.addLayout(action_row)
        return box

    # --- carga de archivos -----------------------------------------------------

    def _load_image(self, path):
        image = media_info.load_image(path)
        self._image = image
        return f"{image.width} × {image.height} px", pil_to_pixmap(image)

    def _load_audio(self, path):
        duration = media_info.get_audio_duration(path)
        self._duration = duration
        return f"Duración: {format_duration(duration)}", None

    def _on_image_changed(self):
        if self.slot_image.path is None:
            self._image = None
        self.preview.set_image(self._image)
        self._update_export_enabled()

    def _on_audio_changed(self):
        if self.slot_audio.path is None:
            self._duration = 0
        self._update_export_enabled()

    # --- ajustes ---------------------------------------------------------------

    def _on_ratio_changed(self, ratio):
        self.preview.set_ratio(*presets.ASPECT_RATIOS[ratio])
        self._update_dimensions()

    def _update_dimensions(self):
        width, height = presets.get_dimensions(
            self.combo_ratio.currentText(), self.combo_resolution.currentData())
        self.label_dimensions.setText(f"{width} × {height}")

    def _update_export_enabled(self):
        ready = self.slot_image.path and self.slot_audio.path and self._worker is None
        self.btn_export.setEnabled(bool(ready))

    # --- ruta de exportación ---------------------------------------------------

    def _change_folder(self):
        current = export_path.resolve_path(self.input_path.text()).parent
        folder = QFileDialog.getExistingDirectory(
            self, "Carpeta de exportación", str(current))
        if folder:
            self.input_path.setText(
                export_path.change_folder(self.input_path.text(), folder))

    def _renew_default_name(self):
        """Si el nombre sigue siendo el uuid generado, asigna uno nuevo."""
        path = Path(self.input_path.text().strip())
        if path.name == self._generated_name:
            self._generated_name = f"{uuid.uuid4()}.mp4"
            self.input_path.setText(str(path.with_name(self._generated_name)))

    # --- exportación -----------------------------------------------------------

    def _start_export(self):
        if not self.input_path.text().strip():
            QMessageBox.warning(self, APP_NAME, "Indica la ruta de exportación.")
            return
        output = export_path.resolve_path(self.input_path.text())
        self._output = output
        self._worker = ExportWorker({
            "image": self.slot_image.path,
            "audio": self.slot_audio.path,
            "output": output,
            "aspect_ratio": self.combo_ratio.currentText(),
            "short_side": self.combo_resolution.currentData(),
            "fps": self.fps_group.checkedId(),
            "fit_mode": self.combo_fit.currentData(),
            "duration": self._duration,
        }, self)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.succeeded.connect(self._on_export_succeeded)
        self._worker.failed.connect(self._on_export_failed)
        self._worker.cancelled.connect(self._on_export_cancelled)
        self._worker.finished.connect(self._on_worker_finished)

        self.progress.setValue(0)
        self.btn_cancel.show()
        self.btn_cancel.setEnabled(True)
        self._update_export_enabled()
        self._worker.start()

    def _cancel_export(self):
        self.btn_cancel.setEnabled(False)
        self._worker.cancel()

    def _on_worker_finished(self):
        self._worker.deleteLater()
        self._worker = None
        self.btn_cancel.hide()
        self._update_export_enabled()

    def _on_export_succeeded(self):
        self.progress.setValue(100)
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setText(f"Video exportado:\n{self._output}")
        open_button = box.addButton("Abrir carpeta", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Ok)
        box.exec()
        if box.clickedButton() is open_button:
            os.startfile(self._output.parent)
        self._renew_default_name()

    def _on_export_failed(self, message):
        self.progress.setValue(0)
        QMessageBox.critical(self, APP_NAME, f"No se pudo exportar el video:\n{message}")

    def _on_export_cancelled(self):
        self.progress.setValue(0)

    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait()
        super().closeEvent(event)
