import subprocess
import sys
import threading

import imageio_ffmpeg

from tracktube.core.ffmpeg_cmd import build_command


class ExportError(Exception):
    pass


class ExportCancelled(Exception):
    pass


def get_ffmpeg_exe():
    return imageio_ffmpeg.get_ffmpeg_exe()


def export_video(image, audio, output, aspect_ratio, short_side, fps, fit_mode,
                 duration, background="ninguno", background_image=None, shadow=False,
                 margin=0, on_progress=None, cancel_event=None):
    """Ejecuta FFmpeg y reporta el progreso (0-100) mediante on_progress.

    Bloqueante: pensado para correr en un hilo. Si cancel_event se activa,
    termina FFmpeg, borra el archivo parcial y lanza ExportCancelled.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_command(get_ffmpeg_exe(), image, audio, output,
                        aspect_ratio, short_side, fps, fit_mode,
                        background, background_image, shadow, margin)

    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", creationflags=flags,
    )

    # Vigila la cancelación sin bloquear la lectura de la salida de FFmpeg
    stop_watcher = threading.Event()

    def _watch_cancel():
        while not stop_watcher.wait(0.2):
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                return

    if cancel_event is not None:
        threading.Thread(target=_watch_cancel, daemon=True).start()

    log = []
    try:
        for line in process.stdout:
            line = line.strip()
            if line.startswith("out_time_us="):
                value = line.split("=", 1)[1]
                if value.isdigit() and on_progress and duration > 0:
                    percent = min(100, int(value) / 1_000_000 / duration * 100)
                    on_progress(percent)
            elif "=" not in line and line:
                log.append(line)
        process.wait()
    finally:
        stop_watcher.set()

    if cancel_event is not None and cancel_event.is_set():
        output.unlink(missing_ok=True)
        raise ExportCancelled()
    if process.returncode != 0:
        output.unlink(missing_ok=True)
        raise ExportError("\n".join(log) or f"FFmpeg terminó con código {process.returncode}")
    if on_progress:
        on_progress(100)
