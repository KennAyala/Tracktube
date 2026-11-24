import base64
import io
from dataclasses import dataclass
from pathlib import Path

import mutagen
import mutagen.flac
import mutagen.mp4
from PIL import Image, UnidentifiedImageError

from tracktube.i18n import tr

# Nombre del formato según la clase de mutagen que lee el archivo
AUDIO_FORMATS = {
    "MP3": "MP3",
    "FLAC": "FLAC",
    "WAVE": "WAV",
    "OggVorbis": "OGG Vorbis",
    "OggOpus": "OGG Opus",
    "AAC": "AAC",  # flujo AAC sin contenedor (.aac)
}


@dataclass
class AudioInfo:
    duration: float          # segundos
    format: str
    bitrate: int | None      # bits por segundo
    bit_depth: int | None    # solo en formatos sin pérdida (WAV, FLAC, M4A ALAC)


def get_audio_info(path):
    """Lee la información del audio. Lanza ValueError si no se puede leer."""
    try:
        audio = mutagen.File(path)
    except Exception as e:
        raise ValueError(tr("error.audio_read", error=e)) from e
    if audio is None or audio.info is None or not audio.info.length:
        raise ValueError(tr("error.audio_read", error=path))

    info = audio.info
    format_name = AUDIO_FORMATS.get(type(audio).__name__, Path(path).suffix.lstrip(".").upper())
    bitrate = getattr(info, "bitrate", None)
    bit_depth = getattr(info, "bits_per_sample", None)
    if isinstance(audio, mutagen.mp4.MP4):
        # .m4a puede ser AAC (con pérdida) o ALAC (sin pérdida). mutagen informa 16 bits
        # también para AAC, pero ahí la profundidad de bits no existe.
        lossless = getattr(info, "codec", "") == "alac"
        format_name = "M4A (ALAC)" if lossless else "M4A (AAC)"
        if not lossless:
            bit_depth = None
    return AudioInfo(
        duration=float(info.length),
        format=format_name,
        bitrate=int(bitrate) if bitrate else None,
        bit_depth=bit_depth or None,
    )


@dataclass
class EmbeddedCover:
    data: bytes
    mime: str
    size: tuple[int, int] | None = None  # (ancho, alto); None si no se pudo leer


FRONT_COVER = 3  # tipo de imagen "portada" en ID3 y FLAC


def get_embedded_cover(path):
    """Busca una imagen en los tags del audio. Devuelve EmbeddedCover o None.

    Lee ID3 (MP3, WAV), imágenes de FLAC y METADATA_BLOCK_PICTURE (OGG Vorbis y Opus).
    Si hay varias prefiere la portada; si el archivo no se puede leer devuelve None.
    """
    try:
        audio = mutagen.File(path)
    except Exception:
        return None
    if audio is None:
        return None

    pictures = []  # (tipo, mime, datos)
    tags = audio.tags
    if isinstance(tags, mutagen.mp4.MP4Tags):  # M4A: átomo «covr», sin tipo de imagen
        for cover in tags.get("covr", []):
            is_png = cover.imageformat == mutagen.mp4.MP4Cover.FORMAT_PNG
            pictures.append((FRONT_COVER, "image/png" if is_png else "image/jpeg", bytes(cover)))
    elif hasattr(tags, "getall"):  # ID3
        pictures += [(frame.type, frame.mime, frame.data) for frame in tags.getall("APIC")]
    elif tags is not None:  # comentarios Vorbis
        for encoded in tags.get("metadata_block_picture", []):
            try:
                picture = mutagen.flac.Picture(base64.b64decode(encoded))
            except (ValueError, mutagen.MutagenError):
                continue
            pictures.append((picture.type, picture.mime, picture.data))
    for picture in getattr(audio, "pictures", None) or []:  # FLAC
        pictures.append((picture.type, picture.mime, picture.data))

    pictures = [picture for picture in pictures if picture[2]]
    if not pictures:
        return None
    picture_type, mime, data = next(
        (picture for picture in pictures if picture[0] == FRONT_COVER), pictures[0])
    try:
        with Image.open(io.BytesIO(data)) as image:  # solo lee la cabecera
            size = image.size
    except (UnidentifiedImageError, OSError):
        size = None
    return EmbeddedCover(data=bytes(data), mime=mime, size=size)


def save_embedded_cover(cover, folder):
    """Guarda la imagen incrustada en `folder` y devuelve su ruta.

    JPG, PNG y BMP se guardan tal cual; otros formatos se convierten a PNG.
    Lanza ValueError si los datos no son una imagen válida.
    """
    folder = Path(folder)
    try:
        with Image.open(io.BytesIO(cover.data)) as image:
            image.load()
            extension = {"JPEG": ".jpg", "PNG": ".png", "BMP": ".bmp"}.get(image.format)
            path = folder / f"metadata-cover{extension or '.png'}"
            if extension:
                path.write_bytes(cover.data)
            else:
                image.save(path, "PNG")
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(tr("error.image_read", error=e)) from e
    return path


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
