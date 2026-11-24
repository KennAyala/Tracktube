from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QPushButton, QStyle

from tracktube.i18n import tr
from tracktube.log import logger
from tracktube.ui.file_slot import FileSlot


class AudioSlot(FileSlot):
    """FileSlot de audio con un botón para escuchar y detener la vista previa."""

    def __init__(self, title_key, extensions, loader, parent=None):
        super().__init__(title_key, extensions, loader, parent)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._update_play_button)
        self.player.errorOccurred.connect(self._on_player_error)

        self.btn_play = QPushButton()
        self.btn_play.hide()
        self.btn_play.clicked.connect(self._toggle_playback)
        self.buttons_layout.insertWidget(0, self.btn_play)

        self.changed.connect(self._on_file_changed)
        self._update_play_button()

    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlayingState

    def stop_preview(self):
        self.player.stop()

    def retranslate(self):
        super().retranslate()
        if hasattr(self, "btn_play"):  # se llama también desde el constructor de FileSlot
            self._update_play_button()

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

    def _on_player_error(self, error, message):
        logger.error("Audio preview error: %s (%s)", message, error)
        self.player.stop()
