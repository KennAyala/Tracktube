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


@pytest.mark.parametrize("fit_mode", ["ajustar", "cortar", "estirar", "desenfocado"])
def test_exporta_mp4_con_caracteristicas_de_youtube(media, tmp_path, fit_mode):
    image, audio = media
    output = tmp_path / "salida" / "video.mp4"
    progress = []
    export_video(image, audio, output, "16:9", 480, 30, fit_mode,
                 duration=3, on_progress=progress.append)

    info = probe(output)
    assert output.exists()
    assert "h264 (High)" in info
    assert "yuv420p" in info and "bt709" in info
    assert "854x480" in info
    assert re.search(r"\b30 fps\b", info)
    assert "aac (LC)" in info and "48000 Hz, stereo" in info
    assert progress and progress[-1] == 100


def test_cancelar_borra_el_archivo(media, tmp_path):
    image, audio = media
    output = tmp_path / "cancelado.mp4"
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(ExportCancelled):
        export_video(image, audio, output, "1:1", 480, 60, "ajustar",
                     duration=3, cancel_event=cancel)
    assert not output.exists()
