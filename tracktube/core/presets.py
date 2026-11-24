"""Resoluciones, aspect ratios, fps y bitrates recomendados por YouTube.

Referencia: https://support.google.com/youtube/answer/1722171
"""

# Aspect ratios como (ancho, alto)
ASPECT_RATIOS = {
    "1:1": (1, 1),
    "4:3": (4, 3),
    "5:4": (5, 4),
    "16:9": (16, 9),
    "3:4": (3, 4),
    "4:5": (4, 5),
    "9:16": (9, 16),
}
DEFAULT_ASPECT_RATIO = "16:9"

# Ratios base (horizontales); la orientación vertical los invierte (4:3 -> 3:4)
BASE_ASPECT_RATIOS = ("1:1", "4:3", "5:4", "16:9")

# La resolución se toma por el lado corto (480p, 720p, ...)
RESOLUTIONS = (480, 720, 1080, 1440, 2160)
DEFAULT_RESOLUTION = 1080

# Mínimo práctico para una imagen fija: 1 fps (también es el valor por defecto)
MIN_FPS = 1
FPS_OPTIONS = (MIN_FPS, 15, 24, 30, 60)
DEFAULT_FPS = MIN_FPS

# Bitrate de video SDR en kbps, por lado corto.
# (hasta 30 fps, de 48 a 60 fps)
VIDEO_BITRATES_KBPS = {
    480: (2500, 4000),
    720: (5000, 7500),
    1080: (8000, 12000),
    1440: (16000, 24000),
    2160: (40000, 60000),
}

# Duración máxima (en segundos) con la que YouTube puede tratar un video como Short
SHORTS_MAX_SECONDS = 180

AUDIO_BITRATE_KBPS = 384
AUDIO_SAMPLE_RATE = 48000


def _even(value):
    """Redondea al par más cercano (yuv420p exige dimensiones pares)."""
    return int(round(value / 2)) * 2


def get_aspect_ratio(base_ratio, vertical):
    """Devuelve la clave de ASPECT_RATIOS para un ratio base y una orientación."""
    if not vertical:
        return base_ratio
    ratio_w, ratio_h = base_ratio.split(":")
    return f"{ratio_h}:{ratio_w}"


def is_horizontal(aspect_ratio):
    ratio_w, ratio_h = ASPECT_RATIOS[aspect_ratio]
    return ratio_w > ratio_h


def may_be_short(duration, aspect_ratio):
    """True si el video podría clasificarse como YouTube Short.

    Pasa con un video de 3:00 o menos que no sea horizontal (1:1 o vertical).
    """
    return (duration > 0 and round(duration) <= SHORTS_MAX_SECONDS
            and not is_horizontal(aspect_ratio))


def get_dimensions(aspect_ratio, short_side):
    """Devuelve (ancho, alto) para un ratio y un lado corto dados."""
    ratio_w, ratio_h = ASPECT_RATIOS[aspect_ratio]
    if ratio_w >= ratio_h:
        return _even(short_side * ratio_w / ratio_h), short_side
    return short_side, _even(short_side * ratio_h / ratio_w)


def get_video_bitrate_kbps(short_side, fps):
    normal, high = VIDEO_BITRATES_KBPS[short_side]
    return high if fps > 30 else normal


def get_gop(fps):
    """GOP de la mitad del frame rate, mínimo 1."""
    return max(1, fps // 2)
