from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QLabel, QPushButton, QStyle

from tracktube.i18n import tr
from tracktube.log import logger
from tracktube.ui.file_slot import FileSlot

# Verde y rojo legibles sobre fondo claro y oscuro
COVER_COLORS = {
    "light": {"yes": "#1a7f37", "no": "#cf222e"},
    "dark": {"yes": "#3fb950", "no": "#f85149"},
}


class AudioSlot(FileSlot):
    """FileSlot de audio con vista previa (Reproducir/Detener) y aviso de imagen en los tags."""

    def __init__(self, title_key, extensions, loader, parent=None):
        super().__init__(title_key, extensions, loader, parent)
        self._cover = None  # imagen incrustada en los tags (EmbeddedCover) o None

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._update_play_button)
        self.player.errorOccurred.connect(self._on_player_error)

        self.btn_play = QPushButton()
        self.btn_play.hide()
        self.btn_play.clicked.connect(self._toggle_playback)
        self.buttons_layout.insertWidget(0, self.btn_play)

        # «Album art in metadata: Yes (600 × 600)» en verde, o «No», debajo de la información
        self.label_cover = QLabel()
        self.label_cover.setTextFormat(Qt.RichText)
        self.label_cover.hide()
        self.add_info_widget(self.label_cover)

        self.changed.connect(self._on_file_changed)
        self._update_play_button()
        self._update_cover_label()

    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlayingState

    def stop_preview(self):
        self.player.stop()

    def set_embedded_cover(self, cover):
        """Indica si el audio cargado trae una imagen en sus tags (EmbeddedCover o None)."""
        self._cover = cover
        self._update_cover_label()

    def retranslate(self):
        super().retranslate()
        if hasattr(self, "btn_play"):  # se llama también desde el constructor de FileSlot
            self._update_play_button()
            self._update_cover_label()

    def changeEvent(self, event):
        if event.type() == QEvent.PaletteChange and hasattr(self, "label_cover"):
            self._update_cover_label()  # los colores dependen del tema claro u oscuro
        super().changeEvent(event)

    def _toggle_playback(self):
        if self.is_playing():
            self.player.stop()
            logger.debug("Audio preview stopped")
        else:
            self.player.play()
            logger.debug("Audio preview started")

    def _on_file_changed(self):
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(self.path) if self.path else QUrl())
        self.btn_play.setVisible(self.path is not None)

    def _update_play_button(self, *_):
        playing = self.is_playing()
        icon = QStyle.SP_MediaStop if playing else QStyle.SP_MediaPlay
        self.btn_play.setIcon(self.style().standardIcon(icon))
        self.btn_play.setText(tr("audio.stop" if playing else "audio.play"))
        self.btn_play.setToolTip(tr("audio.preview_tip"))

    def _update_cover_label(self):
        if self.path is None:
            self.label_cover.hide()
            return
        colors = COVER_COLORS["dark" if self.palette().window().color().lightness() < 128
                              else "light"]
        if self._cover is None:
            state, color = tr("audio.cover_no"), colors["no"]
        elif self._cover.size:
            width, height = self._cover.size
            state = tr("audio.cover_yes_size", width=width, height=height)
            color = colors["yes"]
        else:
            state, color = tr("audio.cover_yes"), colors["yes"]
        self.label_cover.setText(
            f'{tr("audio.cover_label")}: <b><span style="color:{color}">{state}</span></b>')
        self.label_cover.show()

    def _on_player_error(self, error, message):
        logger.error("Audio preview error: %s (%s)", message, error)
        self.player.stop()
