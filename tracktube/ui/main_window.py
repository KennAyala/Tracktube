import re
import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QRadioButton, QSpinBox, QStyle, QToolButton, QVBoxLayout, QWidget,
)

from tracktube.config import APP_NAME, AUDIO_EXTENSIONS, DEFAULT_EXPORT_DIR, IMAGE_EXTENSIONS
from tracktube.core import export_path, media_info, presets
from tracktube.core.fit_modes import (
    BACKGROUNDS, DEFAULT_BACKGROUND, DEFAULT_BLUR, DEFAULT_DARKNESS, DEFAULT_FIT_MODE,
    DEFAULT_MARGIN, FIT_MODES, MAX_BLUR, MAX_DARKNESS, MAX_MARGIN, MIN_MARGIN, render_preview,
)
from tracktube.core.image_export import IMAGE_FILTERS, resolve_image_path, save_image
from tracktube.i18n import DEFAULT_LANGUAGE, LANGUAGES, get_language, set_language, tr
from tracktube.log import logger
from tracktube.settings import create_settings
from tracktube.ui.audio_slot import AudioSlot
from tracktube.ui.export_worker import ExportWorker
from tracktube.ui.image_slot import ImageSlot
from tracktube.ui.log_panel import LogPanel
from tracktube.ui.preview_widget import PreviewWidget, pil_to_pixmap
from tracktube.ui.theme import DEFAULT_THEME, THEMES, apply_theme

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")

SHORT_WARNING_STYLE = (
    "QLabel { background: #fff3cd; color: #664d03; border: 1px solid #ffda6a;"
    " border-radius: 4px; padding: 6px; }"
)


def format_duration(seconds):
    minutes, secs = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def orientation_icon(vertical, color):
    """Rectángulo horizontal o vertical que indica la orientación."""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QPen(color, 2))
    if vertical:
        painter.drawRect(7, 3, 10, 17)
    else:
        painter.drawRect(3, 7, 17, 10)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.settings = settings or create_settings()
        set_language(self.settings.value("language", DEFAULT_LANGUAGE, type=str))

        # El panel de log se crea primero para registrar desde el arranque
        self.log_panel = LogPanel()
        self.log_panel.hide()
        logger.info("Tracktube started (language=%s)", get_language())

        self._loading = True
        self._image = None
        self._duration = 0
        self._worker = None
        self._background_path = None
        self._background_image = None
        self._progress_state = "idle"
        self._metadata_cover = None  # imagen incrustada en los tags del audio cargado
        self._temp_dir = None        # carpeta temporal donde se guarda esa imagen

        self.slot_image = ImageSlot("slot.image", IMAGE_EXTENSIONS, self._load_image)
        self.slot_audio = AudioSlot("slot.audio", AUDIO_EXTENSIONS, self._load_audio)
        self.slot_image.changed.connect(self._on_image_changed)
        self.slot_image.metadata_cover_requested.connect(self._use_metadata_cover)
        self.slot_audio.changed.connect(self._on_audio_changed)

        self.preview = PreviewWidget()
        self.preview.export_requested.connect(self._export_preview_image)

        self.label_short_warning = QLabel()
        self.label_short_warning.setWordWrap(True)
        self.label_short_warning.setStyleSheet(SHORT_WARNING_STYLE)
        self.label_short_warning.hide()

        self.btn_log = QPushButton()
        self.btn_log.setCheckable(True)
        self.btn_log.toggled.connect(self._toggle_log)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.addLayout(self._build_header())

        content = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(self.slot_audio)
        left.addWidget(self.slot_image)
        left.addWidget(self._build_settings())
        left.addWidget(self.label_short_warning)
        left.addWidget(self._build_export())
        left.addStretch(1)
        content.addLayout(left, 1)
        content.addWidget(self.preview)
        content.addWidget(self.log_panel)
        root.addLayout(content)

        self._load_settings()
        self._connect_persistence()
        self._loading = False
        logger.debug("Settings loaded")
        self.retranslate_ui()
        self._on_ratio_changed()
        self._on_options_changed()
        self._update_export_enabled()

    # --- construcción de la UI -------------------------------------------------

    def _build_header(self):
        self.label_theme = QLabel()
        self.combo_theme = QComboBox()
        for theme in THEMES:  # "Sistema" va primero y es el valor por defecto
            self.combo_theme.addItem("", theme)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)

        self.label_language = QLabel()
        self.combo_language = QComboBox()
        for code, name in LANGUAGES.items():
            self.combo_language.addItem(name, code)
        self.combo_language.setCurrentIndex(self.combo_language.findData(get_language()))
        self.combo_language.currentIndexChanged.connect(self._on_language_changed)

        header = QHBoxLayout()
        header.addWidget(self.btn_log)
        header.addStretch(1)
        header.addWidget(self.label_theme)
        header.addWidget(self.combo_theme)
        header.addSpacing(12)
        header.addWidget(self.label_language)
        header.addWidget(self.combo_language)
        return header

    def _build_settings(self):
        self.group_settings = QGroupBox()
        grid = QGridLayout(self.group_settings)

        # Aspect ratio + orientación (horizontal primero, por defecto)
        self.combo_ratio = QComboBox()
        for base_ratio in presets.BASE_ASPECT_RATIOS:
            self.combo_ratio.addItem(base_ratio, base_ratio)
        self.combo_ratio.setCurrentIndex(
            self.combo_ratio.findData(presets.DEFAULT_ASPECT_RATIO))
        self.btn_horizontal = QToolButton()
        self.btn_vertical = QToolButton()
        self.orientation_group = QButtonGroup(self)
        for button in (self.btn_horizontal, self.btn_vertical):
            button.setIconSize(QSize(24, 24))
            button.setCheckable(True)
            self.orientation_group.addButton(button)
        self.btn_horizontal.setChecked(True)
        self._update_orientation_icons()
        ratio_row = QHBoxLayout()
        ratio_row.addWidget(self.combo_ratio, 1)
        ratio_row.addWidget(self.btn_horizontal)
        ratio_row.addWidget(self.btn_vertical)

        self.combo_resolution = QComboBox()
        for short_side in presets.RESOLUTIONS:
            self.combo_resolution.addItem(f"{short_side}p", short_side)
        self.combo_resolution.setCurrentIndex(
            self.combo_resolution.findData(presets.DEFAULT_RESOLUTION))
        self.label_dimensions = QLabel()

        self.combo_fit = QComboBox()
        for key in FIT_MODES:
            self.combo_fit.addItem("", key)
        self.combo_fit.setCurrentIndex(self.combo_fit.findData(DEFAULT_FIT_MODE))

        # Fondo, sombra y margen (solo aplican al modo "Ajustar")
        self.combo_background = QComboBox()
        for key in BACKGROUNDS:
            self.combo_background.addItem("", key)
        self.combo_background.setCurrentIndex(
            self.combo_background.findData(DEFAULT_BACKGROUND))
        self.btn_background = QPushButton()
        self.btn_background.clicked.connect(self._choose_background)
        self.label_background_file = QLabel()
        self.background_row = QWidget()
        background_layout = QHBoxLayout(self.background_row)
        background_layout.setContentsMargins(0, 0, 0, 0)
        background_layout.addWidget(self.btn_background)
        background_layout.addWidget(self.label_background_file, 1)

        # Desenfoque y oscuridad se muestran siempre; se habilitan solo cuando hay un fondo
        # desenfocado o un fondo, respectivamente
        self.spin_blur = QSpinBox()
        self.spin_blur.setRange(0, MAX_BLUR)
        self.spin_blur.setSuffix(" %")
        self.spin_blur.setValue(DEFAULT_BLUR)
        self.btn_blur_reset = self._reset_button(self.spin_blur, DEFAULT_BLUR)

        self.spin_darkness = QSpinBox()
        self.spin_darkness.setRange(0, MAX_DARKNESS)
        self.spin_darkness.setSuffix(" %")
        self.spin_darkness.setValue(DEFAULT_DARKNESS)
        self.btn_darkness_reset = self._reset_button(self.spin_darkness, DEFAULT_DARKNESS)

        self.check_shadow = QCheckBox()
        self.spin_margin = QSpinBox()
        self.spin_margin.setRange(MIN_MARGIN, MAX_MARGIN)  # negativo: acerca la imagen
        self.spin_margin.setSuffix(" %")
        self.spin_margin.setValue(DEFAULT_MARGIN)
        self.btn_margin_reset = self._reset_button(self.spin_margin, DEFAULT_MARGIN)

        self.fps_group = QButtonGroup(self)
        fps_layout = QHBoxLayout()
        for fps in presets.FPS_OPTIONS:
            radio = QRadioButton(str(fps))
            radio.setChecked(fps == presets.DEFAULT_FPS)
            self.fps_group.addButton(radio, fps)
            fps_layout.addWidget(radio)
        fps_layout.addStretch(1)

        self.label_ratio = QLabel()
        self.label_resolution = QLabel()
        self.label_fit = QLabel()
        self.label_background = QLabel()
        self.label_blur = QLabel()
        self.label_darkness = QLabel()
        self.label_margin = QLabel()
        self.label_fps = QLabel()

        grid.addWidget(self.label_ratio, 0, 0)
        grid.addLayout(ratio_row, 0, 1, 1, 2)
        grid.addWidget(self.label_resolution, 1, 0)
        grid.addWidget(self.combo_resolution, 1, 1)
        grid.addWidget(self.label_dimensions, 1, 2)
        grid.addWidget(self.label_fit, 2, 0)
        grid.addWidget(self.combo_fit, 2, 1, 1, 2)
        grid.addWidget(self.label_background, 3, 0)
        grid.addWidget(self.combo_background, 3, 1, 1, 2)
        grid.addWidget(self.background_row, 4, 1, 1, 2)
        grid.addWidget(self.label_blur, 5, 0)
        grid.addWidget(self.spin_blur, 5, 1)
        grid.addWidget(self.btn_blur_reset, 5, 2)
        grid.addWidget(self.label_darkness, 6, 0)
        grid.addWidget(self.spin_darkness, 6, 1)
        grid.addWidget(self.btn_darkness_reset, 6, 2)
        grid.addWidget(self.label_margin, 7, 0)
        grid.addWidget(self.spin_margin, 7, 1)
        grid.addWidget(self.btn_margin_reset, 7, 2)
        grid.addWidget(self.check_shadow, 8, 0, 1, 3)
        grid.addWidget(self.label_fps, 9, 0)
        grid.addLayout(fps_layout, 9, 1, 1, 2)

        self.combo_ratio.currentIndexChanged.connect(self._on_ratio_changed)
        self.orientation_group.buttonClicked.connect(self._on_ratio_changed)
        self.fps_group.idClicked.connect(lambda fps: logger.debug("FPS: %s", fps))
        self.combo_resolution.currentIndexChanged.connect(self._update_dimensions)
        self.combo_fit.currentIndexChanged.connect(self._on_options_changed)
        self.combo_background.currentIndexChanged.connect(self._on_options_changed)
        self.check_shadow.toggled.connect(self._on_options_changed)
        self.spin_blur.valueChanged.connect(self._on_options_changed)
        self.spin_darkness.valueChanged.connect(self._on_options_changed)
        self.spin_margin.valueChanged.connect(self._on_options_changed)
        return self.group_settings

    @staticmethod
    def _reset_button(spin, default):
        """Botón ✕ que devuelve el campo a su valor por defecto.

        Solo se muestra mientras el valor sea distinto del valor por defecto.
        """
        button = QToolButton()
        button.setText("✕")
        # Oculta conserva su espacio, así el resto de los campos no se mueve al aparecer
        policy = button.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        button.setSizePolicy(policy)
        button.clicked.connect(lambda: spin.setValue(default))
        spin.valueChanged.connect(lambda value: button.setVisible(value != default))
        button.setVisible(spin.value() != default)
        return button

    def _build_export(self):
        self.group_export = QGroupBox()
        layout = QVBoxLayout(self.group_export)

        # Carpeta y nombre de archivo van separados; el botón de refrescar queda
        # a la altura del nombre porque es lo que cambia
        self.label_folder = QLabel()
        self.input_folder = QLineEdit(DEFAULT_EXPORT_DIR)
        self.btn_folder = QPushButton()
        self.btn_folder.clicked.connect(self._change_folder)
        self.label_filename = QLabel()
        self.input_filename = QLineEdit(export_path.new_default_filename())
        self.input_filename.setMinimumWidth(340)  # que quepa un uuid completo con .mp4
        self.btn_refresh_uuid = QToolButton()
        self.btn_refresh_uuid.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh_uuid.clicked.connect(self._refresh_uuid)
        path_grid = QGridLayout()
        path_grid.addWidget(self.label_folder, 0, 0)
        path_grid.addWidget(self.input_folder, 0, 1)
        path_grid.addWidget(self.btn_folder, 0, 2)
        path_grid.addWidget(self.label_filename, 1, 0)
        path_grid.addWidget(self.input_filename, 1, 1)
        path_grid.addWidget(self.btn_refresh_uuid, 1, 2)
        path_grid.setColumnStretch(1, 1)

        self.btn_export = QPushButton()
        self.btn_export.clicked.connect(self._start_export)
        self.btn_cancel = QPushButton()
        self.btn_cancel.clicked.connect(self._cancel_export)
        self.btn_cancel.hide()
        # El estado va en una etiqueta porque el estilo de Windows 11 no dibuja el texto
        # de la barra de progreso
        self.label_progress = QLabel()
        action_row = QHBoxLayout()
        action_row.addWidget(self.btn_export)
        action_row.addWidget(self.btn_cancel)
        action_row.addStretch(1)
        action_row.addWidget(self.label_progress)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.valueChanged.connect(self._update_progress_label)

        layout.addLayout(path_grid)
        layout.addLayout(action_row)
        layout.addWidget(self.progress)
        return self.group_export

    # --- tema ------------------------------------------------------------------

    def _on_theme_changed(self):
        theme = self.combo_theme.currentData()
        logger.info("Theme changed to %s", theme)
        apply_theme(theme)
        self._save_settings()

    def _update_orientation_icons(self):
        """Dibuja los íconos de orientación con el color del tema actual."""
        color = self.palette().color(QPalette.ButtonText)
        self.btn_horizontal.setIcon(orientation_icon(False, color))
        self.btn_vertical.setIcon(orientation_icon(True, color))

    def changeEvent(self, event):
        if event.type() == QEvent.PaletteChange and hasattr(self, "btn_vertical"):
            self._update_orientation_icons()
        super().changeEvent(event)

    # --- idioma ----------------------------------------------------------------

    def _on_language_changed(self):
        set_language(self.combo_language.currentData())
        logger.info("Language changed to %s", get_language())
        self.retranslate_ui()
        self._save_settings()

    def retranslate_ui(self):
        self.label_theme.setText(f"{tr('header.theme')}:")
        self._retranslate_combo(self.combo_theme, "theme")
        self.label_language.setText(f"{tr('header.language')}:")
        self.slot_image.retranslate()
        self.slot_audio.retranslate()
        self.preview.retranslate()

        self.group_settings.setTitle(tr("settings.title"))
        self.label_ratio.setText(tr("settings.ratio"))
        self.btn_horizontal.setToolTip(tr("settings.horizontal"))
        self.btn_vertical.setToolTip(tr("settings.vertical"))
        self.label_resolution.setText(tr("settings.resolution"))
        self.label_fit.setText(tr("settings.fit"))
        self._retranslate_combo(self.combo_fit, "fit")
        self.label_background.setText(tr("settings.background"))
        self._retranslate_combo(self.combo_background, "background")
        self.btn_background.setText(tr("settings.choose_background"))
        self._update_background_label()
        self.label_blur.setText(tr("settings.blur"))
        self.label_blur.setToolTip(tr("settings.blur_tip"))
        self.spin_blur.setToolTip(tr("settings.blur_tip"))
        self.btn_blur_reset.setToolTip(tr("settings.blur_reset"))
        self.label_darkness.setText(tr("settings.darkness"))
        self.label_darkness.setToolTip(tr("settings.darkness_tip"))
        self.spin_darkness.setToolTip(tr("settings.darkness_tip"))
        self.btn_darkness_reset.setToolTip(tr("settings.darkness_reset"))
        self.check_shadow.setText(tr("settings.shadow"))
        self.label_margin.setText(tr("settings.margin"))
        self.spin_margin.setToolTip(tr("settings.margin_tip"))
        self.label_margin.setToolTip(tr("settings.margin_tip"))
        self.btn_margin_reset.setToolTip(tr("settings.margin_reset"))
        self.label_fps.setText(tr("settings.fps"))
        for button in self.fps_group.buttons():
            fps = self.fps_group.id(button)
            if fps == presets.MIN_FPS:
                button.setText(tr("settings.fps_min", fps=fps))

        self.group_export.setTitle(tr("export.title"))
        self.label_folder.setText(tr("export.folder"))
        self.label_filename.setText(tr("export.filename"))
        self.btn_refresh_uuid.setToolTip(tr("export.new_uuid"))
        self.btn_folder.setText(tr("export.change_folder"))
        self.btn_export.setText(tr("export.button"))
        self.btn_cancel.setText(tr("export.cancel"))
        self._update_progress_format()
        self.btn_log.setText(tr("log.button"))
        self._update_short_warning()

    @staticmethod
    def _retranslate_combo(combo, prefix):
        for index in range(combo.count()):
            combo.setItemText(index, tr(f"{prefix}.{combo.itemData(index)}"))

    # --- carga de archivos -----------------------------------------------------

    def _load_image(self, path):
        image = media_info.load_image(path)
        self._image = image
        logger.info("Album art loaded: %s (%d x %d, mode %s)",
                    path, image.width, image.height, image.mode)
        info = ("slot.image_info", {"width": image.width, "height": image.height})
        return info, pil_to_pixmap(image)

    def _load_audio(self, path):
        audio = media_info.get_audio_info(path)
        self._duration = audio.duration
        logger.info("Audio track loaded: %s (%.2fs, %s, bitrate=%s, bit depth=%s)",
                    path, audio.duration, audio.format, audio.bitrate, audio.bit_depth)
        info = ("slot.audio_info", {
            "duration": format_duration(audio.duration),
            "format": audio.format,
            "bitrate": f"{round(audio.bitrate / 1000)} kbps" if audio.bitrate else "—",
            "bit_depth": f"{audio.bit_depth}-bit" if audio.bit_depth else "—",
        })
        return info, None

    def _on_image_changed(self):
        if self.slot_image.path is None:
            self._image = None
            logger.info("Album art removed")
        self.preview.set_image(self._image)
        self._update_export_enabled()

    def _on_audio_changed(self):
        if self.slot_audio.path is None:
            self._duration = 0
            self._metadata_cover = None
            logger.info("Audio track removed")
        else:
            self._metadata_cover = media_info.get_embedded_cover(self.slot_audio.path)
            if self._metadata_cover is None:
                logger.debug("No embedded image found in the audio tags")
            else:
                logger.info("Embedded image found in the audio tags (%s, %d KB)",
                            self._metadata_cover.mime, len(self._metadata_cover.data) // 1024)
        self.slot_image.set_metadata_cover_available(self._metadata_cover is not None)
        self.slot_audio.set_embedded_cover(self._metadata_cover)
        self._update_short_warning()
        self._update_export_enabled()

    def _use_metadata_cover(self):
        """Usa la imagen incrustada en los tags del audio como Album art."""
        if self._metadata_cover is None:
            return
        if self._temp_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="tracktube-")
        try:
            path = media_info.save_embedded_cover(self._metadata_cover, self._temp_dir.name)
        except ValueError as e:
            logger.error("Could not use the embedded image: %s", e)
            QMessageBox.warning(self, tr("slot.image"), str(e))
            return
        logger.info("Using the embedded image as album art: %s", path)
        self.slot_image.set_file(str(path))

    # --- ajustes ---------------------------------------------------------------

    def _current_ratio(self):
        return presets.get_aspect_ratio(
            self.combo_ratio.currentData(), self.btn_vertical.isChecked())

    def _on_ratio_changed(self, *_):
        vertical = self.btn_vertical.isChecked()
        # Los nombres del selector siguen la orientación (16:9 -> 9:16)
        for index in range(self.combo_ratio.count()):
            self.combo_ratio.setItemText(
                index, presets.get_aspect_ratio(self.combo_ratio.itemData(index), vertical))
        # 1:1 no tiene orientación
        has_orientation = self.combo_ratio.currentData() != "1:1"
        self.btn_horizontal.setEnabled(has_orientation)
        self.btn_vertical.setEnabled(has_orientation)
        logger.debug("Aspect ratio: %s", self._current_ratio())
        self.preview.set_ratio(*presets.ASPECT_RATIOS[self._current_ratio()])
        self._update_dimensions()
        self._update_short_warning()

    def _update_dimensions(self):
        width, height = presets.get_dimensions(
            self._current_ratio(), self.combo_resolution.currentData())
        self.label_dimensions.setText(f"{width} × {height}")
        logger.debug("Output size: %d x %d", width, height)

    def _update_short_warning(self):
        """Avisa si el video podría terminar como un YouTube Short."""
        show = presets.may_be_short(self._duration, self._current_ratio())
        if show != self.label_short_warning.isVisibleTo(self):
            logger.warning("YouTube Short warning %s (duration=%.1fs, ratio=%s)",
                           "shown" if show else "hidden", self._duration, self._current_ratio())
        self.label_short_warning.setText(
            f"<b>{tr('warning.short')}</b><br>{tr('warning.short_hint')}")
        self.label_short_warning.setVisible(show)

    def _toggle_log(self, visible):
        self.log_panel.setVisible(visible)
        # Actualiza el layout antes de ajustar para que la ventana crezca o se encoja
        self.centralWidget().layout().activate()
        self.adjustSize()

    def _on_options_changed(self, *_):
        fit_mode = self.combo_fit.currentData()
        background = self.combo_background.currentData()
        framed = fit_mode == "ajustar"
        for widget in (self.label_background, self.combo_background, self.check_shadow,
                       self.label_margin, self.spin_margin, self.btn_margin_reset,
                       self.background_row):
            widget.setEnabled(framed)
        # El desenfoque y la oscuridad se muestran siempre, pero solo se habilitan si hay
        # un fondo desenfocado o un fondo que oscurecer, respectivamente
        has_background = framed and background != DEFAULT_BACKGROUND
        has_blur = framed and background == "desenfocado"
        for widget in (self.label_blur, self.spin_blur, self.btn_blur_reset):
            widget.setEnabled(has_blur)
        for widget in (self.label_darkness, self.spin_darkness, self.btn_darkness_reset):
            widget.setEnabled(has_background)
        self.background_row.setVisible(background == "personalizado")
        logger.debug("Options: fit=%s background=%s blur=%d%% darkness=%d%% shadow=%s margin=%d%%",
                     fit_mode, background, self.spin_blur.value(), self.spin_darkness.value(),
                     self.check_shadow.isChecked(), self.spin_margin.value())
        self.preview.set_options(
            fit_mode, background, self.check_shadow.isChecked(),
            self.spin_margin.value(), self._background_image, self.spin_darkness.value(),
            self.spin_blur.value())

    def _export_preview_image(self):
        """Guarda la vista previa como JPG (por defecto) o PNG con la resolución del video."""
        if self._image is None:
            return
        width, height = presets.get_dimensions(
            self._current_ratio(), self.combo_resolution.currentData())
        start_dir = export_path.build_path(self.input_folder.text(), "x.mp4").parent
        if not start_dir.is_dir():
            start_dir = Path.home()
        # El nombre sugerido es el mismo que tiene el campo de nombre de archivo del video
        name = Path(self.input_filename.text().strip()).stem or "preview"
        path, selected_filter = QFileDialog.getSaveFileName(
            self, tr("preview.export_dialog"), str(start_dir / f"{name}.jpg"), IMAGE_FILTERS)
        if not path:
            return

        target = resolve_image_path(path, selected_filter)
        QApplication.setOverrideCursor(Qt.WaitCursor)  # a 4K el render tarda un momento
        try:
            image = render_preview(
                self._image, self.combo_fit.currentData(), width, height,
                self.combo_background.currentData(), self.check_shadow.isChecked(),
                self.spin_margin.value(), self._background_image, self.spin_darkness.value(),
                self.spin_blur.value())
            save_image(image, target)
        except OSError as e:
            logger.error("Could not save the preview image: %s", e)
            QMessageBox.warning(self, APP_NAME, tr("msg.image_save_failed", error=e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        logger.info("Preview exported as image: %s (%d x %d)", target, width, height)

    def _choose_background(self):
        patterns = " ".join(f"*{ext}" for ext in IMAGE_EXTENSIONS)
        title = tr("settings.background_dialog")
        path, _ = QFileDialog.getOpenFileName(
            self, title, "", f"{title} ({patterns})")
        if path:
            self._set_background_image(path, warn=True)
            self._on_options_changed()
            self._save_settings()

    def _set_background_image(self, path, warn=False):
        try:
            self._background_image = media_info.load_image(path)
        except ValueError as e:
            if warn:
                QMessageBox.warning(self, APP_NAME, str(e))
            return
        self._background_path = path
        logger.info("Custom background loaded: %s", path)
        self._update_background_label()

    def _update_background_label(self):
        self.label_background_file.setText(
            Path(self._background_path).name if self._background_path else "")

    def _update_export_enabled(self):
        ready = self.slot_image.path and self.slot_audio.path and self._worker is None
        self.btn_export.setEnabled(bool(ready))

    # --- ruta de exportación ---------------------------------------------------

    def _change_folder(self):
        current = export_path.build_path(
            self.input_folder.text(), self.input_filename.text() or "a.mp4").parent
        folder = QFileDialog.getExistingDirectory(
            self, tr("export.folder_dialog"), str(current))
        if folder:
            self.input_folder.setText(folder)

    def _refresh_uuid(self):
        """Cambia el nombre del archivo por un uuid nuevo."""
        new_name = export_path.new_default_filename()
        logger.debug("New UUID: %s", new_name)
        self.input_filename.setText(new_name)

    def _renew_uuid(self):
        """Si el nombre del archivo es un uuid, asigna uno nuevo; un nombre propio se respeta."""
        if UUID_PATTERN.match(Path(self.input_filename.text().strip()).stem):
            self._refresh_uuid()

    def _confirm_overwrite(self, output):
        """Avisa que el archivo ya existe y será reemplazado. Devuelve True si se continúa."""
        box = QMessageBox(QMessageBox.Warning, APP_NAME, tr("msg.overwrite", path=output), parent=self)
        replace_button = box.addButton(tr("msg.replace"), QMessageBox.AcceptRole)
        cancel_button = box.addButton(tr("export.cancel"), QMessageBox.RejectRole)
        box.setDefaultButton(cancel_button)
        box.exec()
        return box.clickedButton() is replace_button

    # --- exportación -----------------------------------------------------------

    def _update_progress_format(self):
        if self._progress_state == "running":
            self.progress.setFormat(f"{tr('export.running')} %p%")
        elif self._progress_state == "done":
            self.progress.setFormat(tr("export.done"))
        else:
            self.progress.setFormat(tr("export.idle"))
        self._update_progress_label()

    def _update_progress_label(self, *_):
        """Muestra el estado de la exportación junto al botón (ej. «Exporting… 45%»)."""
        self.label_progress.setText(
            self.progress.format().replace("%p", str(self.progress.value())))

    def _set_progress_state(self, state, value):
        self._progress_state = state
        self.progress.setValue(value)
        self._update_progress_format()

    def _start_export(self):
        if not self.input_filename.text().strip():
            QMessageBox.warning(self, APP_NAME, tr("msg.no_path"))
            return
        background = self.combo_background.currentData()
        if (self.combo_fit.currentData() == "ajustar" and background == "personalizado"
                and self._background_path is None):
            QMessageBox.warning(self, APP_NAME, tr("msg.no_background"))
            return

        output = export_path.build_path(self.input_folder.text(), self.input_filename.text())
        if output.exists():
            logger.warning("Output file already exists: %s", output)
            if not self._confirm_overwrite(output):
                logger.info("Export cancelled by the user (file not replaced)")
                return
        self._output = output
        logger.info("Export requested: ratio=%s %dp %s fps, fit=%s, background=%s, "
                    "blur=%d%%, darkness=%d%%, shadow=%s, margin=%d%%",
                    self._current_ratio(), self.combo_resolution.currentData(),
                    self.fps_group.checkedId(), self.combo_fit.currentData(), background,
                    self.spin_blur.value(), self.spin_darkness.value(),
                    self.check_shadow.isChecked(), self.spin_margin.value())
        self._worker = ExportWorker({
            "image": self.slot_image.path,
            "audio": self.slot_audio.path,
            "output": output,
            "aspect_ratio": self._current_ratio(),
            "short_side": self.combo_resolution.currentData(),
            "fps": self.fps_group.checkedId(),
            "fit_mode": self.combo_fit.currentData(),
            "duration": self._duration,
            "background": background,
            "background_image": self._background_path,
            "blur": self.spin_blur.value(),
            "darkness": self.spin_darkness.value(),
            "shadow": self.check_shadow.isChecked(),
            "margin": self.spin_margin.value(),
        }, self)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.succeeded.connect(self._on_export_succeeded)
        self._worker.failed.connect(self._on_export_failed)
        self._worker.cancelled.connect(self._on_export_cancelled)
        self._worker.finished.connect(self._on_worker_finished)

        self._set_progress_state("running", 0)
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
        self._set_progress_state("done", 100)
        self._renew_uuid()

    def _on_export_failed(self, message):
        logger.error("Export failed: %s", message)
        self._set_progress_state("idle", 0)
        QMessageBox.critical(self, APP_NAME, tr("msg.export_failed", error=message))

    def _on_export_cancelled(self):
        self._set_progress_state("idle", 0)

    # --- configuración guardada ------------------------------------------------

    def _load_settings(self):
        """Restaura los ajustes y la ruta de exportación del usuario."""
        s = self.settings
        self._set_combo_data(self.combo_theme, s.value("theme", DEFAULT_THEME, type=str))
        self._set_combo_data(self.combo_ratio,
                             s.value("ratio", presets.DEFAULT_ASPECT_RATIO, type=str))
        if s.value("vertical", False, type=bool):
            self.btn_vertical.setChecked(True)
        self._set_combo_data(self.combo_resolution,
                             s.value("resolution", presets.DEFAULT_RESOLUTION, type=int))
        self._set_combo_data(self.combo_fit, s.value("fit_mode", DEFAULT_FIT_MODE, type=str))
        self._set_combo_data(self.combo_background,
                             s.value("background", DEFAULT_BACKGROUND, type=str))
        self.spin_blur.setValue(s.value("blur", DEFAULT_BLUR, type=int))
        self.spin_darkness.setValue(s.value("darkness", DEFAULT_DARKNESS, type=int))
        self.check_shadow.setChecked(s.value("shadow", False, type=bool))
        self.spin_margin.setValue(s.value("margin", DEFAULT_MARGIN, type=int))
        button = self.fps_group.button(s.value("fps", presets.DEFAULT_FPS, type=int))
        if button is not None:
            button.setChecked(True)

        background_path = s.value("background_image", "", type=str)
        if background_path and Path(background_path).is_file():
            self._set_background_image(background_path)

        folder = s.value("export_folder", "", type=str).strip()
        filename = s.value("export_filename", "", type=str).strip()
        legacy_path = s.value("export_path", "", type=str).strip()  # versión anterior
        if not (folder or filename) and legacy_path:
            folder, filename = str(Path(legacy_path).parent), Path(legacy_path).name
        if folder:
            self.input_folder.setText(folder)
        # Al abrir la app el uuid siempre es nuevo; un nombre escrito a mano se respeta.
        if filename:
            self.input_filename.setText(filename)
            self._renew_uuid()

    @staticmethod
    def _set_combo_data(combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _connect_persistence(self):
        self.combo_ratio.currentIndexChanged.connect(self._save_settings)
        self.orientation_group.buttonClicked.connect(self._save_settings)
        self.combo_resolution.currentIndexChanged.connect(self._save_settings)
        self.combo_fit.currentIndexChanged.connect(self._save_settings)
        self.combo_background.currentIndexChanged.connect(self._save_settings)
        self.check_shadow.toggled.connect(self._save_settings)
        self.spin_blur.valueChanged.connect(self._save_settings)
        self.spin_darkness.valueChanged.connect(self._save_settings)
        self.spin_margin.valueChanged.connect(self._save_settings)
        self.fps_group.idClicked.connect(self._save_settings)
        self.input_folder.textChanged.connect(self._save_settings)
        self.input_filename.textChanged.connect(self._save_settings)

    def _save_settings(self, *_):
        if self._loading:
            return
        s = self.settings
        s.setValue("language", get_language())
        s.setValue("theme", self.combo_theme.currentData())
        s.setValue("ratio", self.combo_ratio.currentData())
        s.setValue("vertical", self.btn_vertical.isChecked())
        s.setValue("resolution", self.combo_resolution.currentData())
        s.setValue("fit_mode", self.combo_fit.currentData())
        s.setValue("background", self.combo_background.currentData())
        s.setValue("background_image", self._background_path or "")
        s.setValue("blur", self.spin_blur.value())
        s.setValue("darkness", self.spin_darkness.value())
        s.setValue("shadow", self.check_shadow.isChecked())
        s.setValue("margin", self.spin_margin.value())
        s.setValue("fps", self.fps_group.checkedId())
        s.setValue("export_folder", self.input_folder.text())
        s.setValue("export_filename", self.input_filename.text())
        s.sync()  # escribe user/conf.ini ya, sin esperar a que se cierre la app

    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait()
        self._save_settings()
        if self._temp_dir is not None:  # imagen de metadatos guardada temporalmente
            self._temp_dir.cleanup()
            self._temp_dir = None
        logger.info("Tracktube closed")
        self.log_panel.detach()
        super().closeEvent(event)
