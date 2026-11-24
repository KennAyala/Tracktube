from dataclasses import dataclass
from pathlib import Path

import mutagen
from PIL import Image, UnidentifiedImageError

from tracktube.i18n import tr

# Nombre del formato según la clase de mutagen que lee el archivo
AUDIO_FORMATS = {
    "MP3": "MP3",
    "FLAC": "FLAC",
    "WAVE": "WAV",
    "OggVorbis": "OGG Vorbis",
    "OggOpus": "OGG Opus",
}


@dataclass
class AudioInfo:
    duration: float          # segundos
    format: str
    bitrate: int | None      # bits por segundo
    bit_depth: int | None    # solo en formatos sin pérdida (WAV, FLAC)


def get_audio_info(path):
    """Lee la información del audio. Lanza ValueError si no se puede leer."""
    try:
        audio = mutagen.File(path)
    except Exception as e:
        raise ValueError(tr("error.audio_read", error=e)) from e
    if audio is None or audio.info is None or not audio.info.length:
        raise ValueError(tr("error.audio_read", error=path))

    info = audio.info
    return AudioInfo(
        duration=float(info.length),
        format=AUDIO_FORMATS.get(type(audio).__name__, Path(path).suffix.lstrip(".").upper()),
        bitrate=getattr(info, "bitrate", None) or None,
        bit_depth=getattr(info, "bits_per_sample", None) or None,
    )


def get_audio_duration(path):
    """Duración del audio en segundos. Lanza ValueError si no se puede leer."""
    return get_audio_info(path).duration


def has_transparency(image):
    """True si la imagen PIL tiene canal alfa o transparencia indexada (PNG)."""
    return image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info


def load_image(path):
    """Abre y valida la imagen. Lanza ValueError si no es válida."""
    try:
        with Image.open(path) as image:
            image.load()
            return image.copy()
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(tr("error.image_read", error=e)) from e
