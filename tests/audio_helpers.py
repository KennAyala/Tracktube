"""Crea audios de prueba (con y sin imagen incrustada en los tags)."""
import base64
import io
import subprocess
import wave

import pytest
from PIL import Image

from tracktube.core.exporter import get_ffmpeg_exe

CODECS = {"mp3": "libmp3lame", "ogg": "libvorbis", "flac": "flac"}


def make_wav(path, seconds=2, rate=8000, bits=16):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(bits // 8)
        wav.setframerate(rate)
        wav.writeframes(b"\x00" * (bits // 8) * rate * seconds)
    return path


def make_audio(tmp_path, extension, name="audio"):
    """Crea un audio vacío (sin tags) en el formato pedido; se omite la prueba si FFmpeg no puede."""
    wav = make_wav(tmp_path / f"{name}-source.wav", rate=44100)
    if extension == "wav":
        return wav
    out = tmp_path / f"{name}.{extension}"
    result = subprocess.run(
        [get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(wav), "-c:a", CODECS[extension],
         str(out)], capture_output=True)
    if result.returncode != 0:
        pytest.skip(f"este FFmpeg no incluye {CODECS[extension]}")
    return out


def image_bytes(format="PNG", size=(120, 80), color=(200, 40, 60)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format)
    return buffer.getvalue()


def embed_cover(path, extension, data, mime="image/png", picture_type=3):
    """Incrusta una imagen en los tags del audio (ID3, bloque de FLAC o comentario Vorbis)."""
    import mutagen.flac
    from mutagen.id3 import APIC, ID3, ID3NoHeaderError

    if extension in ("mp3", "wav"):
        frame = APIC(encoding=3, mime=mime, type=picture_type, desc="Cover", data=data)
        if extension == "wav":
            from mutagen.wave import WAVE

            audio = WAVE(str(path))
            audio.add_tags()
            audio.tags.add(frame)
            audio.save()
        else:
            try:
                tags = ID3(str(path))
            except ID3NoHeaderError:
                tags = ID3()
            tags.add(frame)
            tags.save(str(path))
        return

    picture = mutagen.flac.Picture()
    picture.data, picture.mime, picture.type = data, mime, picture_type
    picture.width, picture.height, picture.depth = 120, 80, 24
    if extension == "flac":
        audio = mutagen.flac.FLAC(str(path))
        audio.add_picture(picture)
    else:  # ogg: imagen codificada en base64 dentro de un comentario Vorbis
        from mutagen.oggvorbis import OggVorbis

        audio = OggVorbis(str(path))
        audio["metadata_block_picture"] = [base64.b64encode(picture.write()).decode("ascii")]
    audio.save()
