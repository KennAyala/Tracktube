import re
import subprocess
import threading
import wave

import pytest
from PIL import Image

from tracktube.core import media_info
from tracktube.core.exporter import ExportCancelled, export_video, get_ffmpeg_exe


@pytest.fixture
def media(tmp_path):
    image = tmp_path / "cover.png"
    Image.new("RGB", (400, 300), (30, 120, 200)).save(image)
    audio = tmp_path / "track.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(b"\x00\x00" * 2 * 44100 * 3)  # 3 s de silencio
    return image, audio


def probe(path):
    result = subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                            capture_output=True, text=True)
    return result.stderr


def test_duracion_del_audio(media):
    assert media_info.get_audio_duration(media[1]) == pytest.approx(3, abs=0.1)


@pytest.mark.parametrize("fit_mode, background, shadow, margin", [
    ("ajustar", "ninguno", False, 0),
    ("ajustar", "ninguno", True, 10),
    ("ajustar", "desenfocado", False, 0),
    ("ajustar", "desenfocado", True, 15),
    ("ajustar", "personalizado", True, 10),
    ("cortar", "ninguno", False, 0),
    ("estirar", "ninguno", False, 0),
])
def test_exporta_mp4_con_caracteristicas_de_youtube(
        media, tmp_path, fit_mode, background, shadow, margin):
    image, audio = media
    output = tmp_path / "salida" / "video.mp4"
    progress = []
    export_video(image, audio, output, "16:9", 480, 30, fit_mode,
                 duration=3, background=background, background_image=image,
                 shadow=shadow, margin=margin, on_progress=progress.append)

    info = probe(output)
    assert output.exists()
    assert "h264 (High)" in info
    assert "yuv420p" in info and "bt709" in info
    assert "854x480" in info
    assert re.search(r"\b30 fps\b", info)
    assert "aac (LC)" in info and "48000 Hz, stereo" in info
    assert progress and progress[-1] == 100


@pytest.mark.parametrize("fit_mode, background", [
    ("ajustar", "ninguno"),
    ("ajustar", "personalizado"),
    ("ajustar", "desenfocado"),
    ("cortar", "ninguno"),
    ("estirar", "ninguno"),
])
def test_png_transparente_no_deja_fondo_blanco(media, tmp_path, fit_mode, background):
    _, audio = media
    # Imagen 16:9 para que llene el cuadro: izquierda transparente (RGB blanco), derecha roja
    art = tmp_path / "transparent.png"
    image = Image.new("RGBA", (854, 480), (255, 255, 255, 0))
    image.paste((255, 0, 0, 255), (427, 0, 854, 480))
    image.save(art)
    custom = tmp_path / "blue.png"
    Image.new("RGB", (200, 200), (0, 0, 255)).save(custom)

    output = tmp_path / "t.mp4"
    export_video(art, audio, output, "16:9", 480, 1, fit_mode, duration=3,
                 background=background, background_image=custom)
    frame = tmp_path / "frame.png"
    subprocess.run([get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", "1",
                    "-i", str(output), "-frames:v", "1", str(frame)], check=True)
    pixels = Image.open(frame).convert("RGB")

    left, right = pixels.getpixel((100, 240)), pixels.getpixel((750, 240))
    assert right[0] > 200 and right[1] < 60 and right[2] < 60  # parte opaca roja
    if background == "personalizado":
        assert left[2] > 200 and left[0] < 60  # se ve el fondo azul
    else:
        assert max(left) < 60  # negro (o fondo oscuro), nunca blanco


def test_la_exportacion_queda_en_el_log(media, tmp_path):
    from test_log import capture
    from tracktube.log import logger

    handler, received = capture()
    try:
        export_video(media[0], media[1], tmp_path / "log.mp4", "16:9", 480, 15,
                     "ajustar", duration=3)
    finally:
        logger.removeHandler(handler)
    text = "\n".join(received)
    assert "Export started" in text
    assert "Command:" in text and "libx264" in text
    assert "ffmpeg: " in text  # salida de FFmpeg
    assert "Progress: 100%" in text
    assert "Export finished" in text


def test_cancelar_borra_el_archivo(media, tmp_path):
    image, audio = media
    output = tmp_path / "cancelado.mp4"
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(ExportCancelled):
        export_video(image, audio, output, "1:1", 480, 60, "ajustar",
                     duration=3, cancel_event=cancel)
    assert not output.exists()
