import re
import subprocess
import sys
import threading
import time

import imageio_ffmpeg
from PIL import Image

from tracktube.core import media_info
from tracktube.core.ffmpeg_cmd import build_command
from tracktube.core.fit_modes import DEFAULT_BLUR
from tracktube.log import logger

# Líneas de progreso de `-progress pipe:1` (clave=valor); el resto es log de FFmpeg
PROGRESS_LINE = re.compile(
    r"^(frame|fps|stream_\d+_\d+_q|bitrate|total_size|out_time_us|out_time_ms|out_time|"
    r"dup_frames|drop_frames|speed|progress)="
)
ERROR_LINES_SHOWN = 10


class ExportError(Exception):
    pass


class ExportCancelled(Exception):
    pass


def get_ffmpeg_exe():
    return imageio_ffmpeg.get_ffmpeg_exe()


def export_video(image, audio, output, aspect_ratio, short_side, fps, fit_mode,
                 duration, background="ninguno", background_image=None, shadow=False,
                 margin=0, darkness=0, blur=DEFAULT_BLUR, on_progress=None, cancel_event=None):
    """Ejecuta FFmpeg y reporta el progreso (0-100) mediante on_progress.

    Bloqueante: pensado para correr en un hilo. Si cancel_event se activa,
    termina FFmpeg, borra el archivo parcial y lanza ExportCancelled.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = get_ffmpeg_exe()
    with Image.open(image) as source:
        transparent = media_info.has_transparency(source)
    cmd = build_command(ffmpeg_exe, image, audio, output,
                        aspect_ratio, short_side, fps, fit_mode,
                        background, background_image, shadow, margin, transparent, darkness,
                        blur)

    logger.info("Export started: %s", output)
    logger.debug("Album art transparency: %s", transparent)
    logger.debug("FFmpeg executable: %s", ffmpeg_exe)
    logger.debug("Command: %s", subprocess.list2cmdline(cmd))
    started = time.monotonic()

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
                logger.debug("Cancel requested, terminating FFmpeg")
                process.terminate()
                return

    if cancel_event is not None:
        threading.Thread(target=_watch_cancel, daemon=True).start()

    log = []
    last_step = -1
    try:
        for line in process.stdout:
            line = line.strip()
            if line.startswith("out_time_us="):
                value = line.split("=", 1)[1]
                if value.isdigit() and duration > 0:
                    percent = min(100, int(value) / 1_000_000 / duration * 100)
                    if on_progress:
                        on_progress(percent)
                    step = int(percent // 10)
                    if step > last_step:
                        last_step = step
                        logger.debug("Progress: %d%%", step * 10)
            elif line and not PROGRESS_LINE.match(line):
                log.append(line)
                logger.debug("ffmpeg: %s", line)
        process.wait()
    finally:
        stop_watcher.set()

    elapsed = time.monotonic() - started
    if cancel_event is not None and cancel_event.is_set():
        output.unlink(missing_ok=True)
        logger.warning("Export cancelled after %.1fs, partial file removed", elapsed)
        raise ExportCancelled()
    if process.returncode != 0:
        output.unlink(missing_ok=True)
        logger.error("FFmpeg failed with exit code %s after %.1fs", process.returncode, elapsed)
        raise ExportError(
            "\n".join(log[-ERROR_LINES_SHOWN:]) or f"FFmpeg exit code {process.returncode}")
    logger.info("Export finished in %.1fs: %s", elapsed, output)
    if on_progress:
        on_progress(100)
