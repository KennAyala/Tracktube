"""Crea audios de prueba (con y sin imagen incrustada en los tags)."""
import base64
import io
import subprocess
import wave

import pytest
from PIL import Image

from tracktube.core.exporter import get_ffmpeg_exe

# formato -> (códec de FFmpeg, extensión del archivo)
CODECS = {
    "mp3": ("libmp3lame", "mp3"),
    "ogg": ("libvorbis", "ogg"),
    "flac": ("flac", "flac"),
    "m4a": ("aac", "m4a"),    # AAC dentro de un contenedor MP4
    "alac": ("alac", "m4a"),  # ALAC (sin pérdida) en un contenedor MP4
    "aac": ("aac", "aac"),    # flujo AAC sin contenedor
}


def make_wav(path, seconds=2, rate=8000, bits=16):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(bits // 8)
        wav.setframerate(rate)
        wav.writeframes(b"\x00" * (bits // 8) * rate * seconds)
    return path


def make_audio(tmp_path, extension, name="audio", tone=False):
    """Crea un audio (sin tags) en el formato pedido; se omite la prueba si FFmpeg no puede.

    Por defecto es silencio; con `tone=True` es un tono de 440 Hz, que da un bitrate real.
    """
    wav = make_wav(tmp_path / f"{name}-source.wav", rate=44100)
    if extension == "wav":
        return wav
    codec, file_extension = CODECS[extension]
    out = tmp_path / f"{name}.{file_extension}"
    source = (["-f", "lavfi", "-i", "sine=frequency=440:duration=2:sample_rate=44100"]
              if tone else ["-i", str(wav)])
    result = subprocess.run(
        [get_ffmpeg_exe(), "-y", "-loglevel", "error", *source, "-c:a", codec, "-b:a", "128k",
         str(out)] if codec != "alac" else
        [get_ffmpeg_exe(), "-y", "-loglevel", "error", *source, "-c:a", codec, str(out)],
        capture_output=True)
    if result.returncode != 0:
        pytest.skip(f"este FFmpeg no incluye {codec}")
    return out


def image_bytes(format="PNG", size=(120, 80), color=(200, 40, 60)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format)
    return buffer.getvalue()


def embed_cover(path, extension, data, mime="image/png", picture_type=3):
    """Incrusta una imagen en los tags del audio (ID3, bloque de FLAC o comentario Vorbis)."""
    import mutagen.flac
    import mutagen.mp4
    from mutagen.id3 import APIC, ID3, ID3NoHeaderError

    if extension in ("m4a", "alac"):  # átomo «covr» del contenedor MP4
        image_format = (mutagen.mp4.MP4Cover.FORMAT_PNG if mime == "image/png"
                        else mutagen.mp4.MP4Cover.FORMAT_JPEG)
        audio = mutagen.mp4.MP4(str(path))
        audio["covr"] = [mutagen.mp4.MP4Cover(data, imageformat=image_format)]
        audio.save()
        return

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
