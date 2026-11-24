import mutagen
from PIL import Image, UnidentifiedImageError

from tracktube.i18n import tr


def get_audio_duration(path):
    """Duración del audio en segundos. Lanza ValueError si no se puede leer."""
    try:
        audio = mutagen.File(path)
    except Exception as e:
        raise ValueError(tr("error.audio_read", error=e)) from e
    if audio is None or audio.info is None or not audio.info.length:
        raise ValueError(tr("error.audio_read", error=path))
    return float(audio.info.length)


def load_image(path):
    """Abre y valida la imagen. Lanza ValueError si no es válida."""
    try:
        with Image.open(path) as image:
            image.load()
            return image.copy()
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(tr("error.image_read", error=e)) from e
