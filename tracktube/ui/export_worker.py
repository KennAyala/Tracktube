import threading

from PySide6.QtCore import QThread, Signal

from tracktube.core.exporter import ExportCancelled, export_video


class ExportWorker(QThread):
    progress = Signal(int)
    succeeded = Signal()
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.params = params
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            export_video(**self.params,
                         on_progress=lambda percent: self.progress.emit(int(percent)),
                         cancel_event=self.cancel_event)
        except ExportCancelled:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))
        else:
            self.succeeded.emit()
