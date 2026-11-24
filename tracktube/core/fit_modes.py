"""Modos de ajuste de la imagen al cuadro del video.

Cada modo tiene dos implementaciones equivalentes:
- build_filter_graph: filtro de FFmpeg para el video final.
- render_preview: la misma lógica con Pillow para el preview de la UI.

Los fondos, su oscuridad, la sombra y el margen solo aplican al modo "ajustar".
"""

import math

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

FIT_MODES = ("ajustar", "cortar", "estirar")
DEFAULT_FIT_MODE = "ajustar"

BACKGROUNDS = ("ninguno", "desenfocado", "personalizado")
DEFAULT_BACKGROUND = "ninguno"

# Margen del album art respecto al borde, en % del lado corto. Un margen negativo
# agranda el album art más allá del cuadro (se acerca y el borde se recorta).
MIN_MARGIN = -50
MAX_MARGIN = 40

# Oscuridad del fondo en %: 0 lo deja igual y 100 lo vuelve negro
MAX_DARKNESS = 100

_SHADOW_OPACITY = 0.6

# Conversión final: BT.709 rango limitado, yuv420p (como pide YouTube)
_OUTPUT = "setsar=1,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"


def _blur_sigma(width, height):
    return max(1, min(width, height) / 25)


def _shadow_params(width, height):
    """Devuelve (sigma, crecimiento, relleno, desplazamiento vertical) de la sombra.

    El crecimiento agranda la sombra respecto al album art por cada lado y el
    relleno deja espacio para que el difuminado no se corte.
    """
    short = min(width, height)
    sigma = short * 0.03
    return sigma, round(short * 0.01), math.ceil(sigma * 3), round(short * 0.02)


def _inset(width, height, margin):
    return round(min(width, height) * margin / 100)


def _darken_filter(darkness):
    """Filtro de FFmpeg que oscurece el color del fondo (el alfa no cambia)."""
    if not darkness:
        return ""
    factor = 1 - darkness / 100
    return f",colorchannelmixer=rr={factor:g}:gg={factor:g}:bb={factor:g}"


def build_filter_graph(mode, width, height, fps, background=DEFAULT_BACKGROUND,
                       shadow=False, margin=0, transparent=False, darkness=0):
    """Devuelve el filter_complex de FFmpeg con salida etiquetada [v].

    El input se lee a 1 fps y `fps` duplica el frame al final, así los
    filtros pesados solo se ejecutan una vez por segundo.
    El fondo "personalizado" toma su imagen del input [2:v] y `darkness` (0-100)
    oscurece el fondo desenfocado o personalizado.
    Si la imagen tiene transparencia (`transparent`), se compone sobre el fondo
    (negro cuando no hay fondo), porque el MP4 no admite canal alfa.
    """
    size = f"{width}:{height}"
    if mode == "ajustar":
        if background == DEFAULT_BACKGROUND and not shadow and margin == 0 and not transparent:
            chain = (
                f"[0:v]scale={size}:force_original_aspect_ratio=decrease,"
                f"pad={size}:(ow-iw)/2:(oh-ih)/2:black,"
            )
        else:
            return _build_framed_graph(
                width, height, fps, background, shadow, margin, darkness)
    elif mode == "cortar":
        chain = (
            f"[0:v]scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},"
        )
    elif mode == "estirar":
        chain = f"[0:v]scale={size},"
    else:
        raise ValueError(f"Modo de ajuste desconocido: {mode}")
    if transparent:
        return (
            f"color=c=black:s={width}x{height}:r=1,format=rgba[base];"
            f"{chain}format=rgba[art];"
            f"[base][art]overlay=0:0:format=auto[flat];"
            f"[flat]{_OUTPUT},fps={fps}[v]"
        )
    return f"{chain}{_OUTPUT},fps={fps}[v]"


def _build_framed_graph(width, height, fps, background, shadow, margin, darkness=0):
    size = f"{width}:{height}"
    inset = _inset(width, height, margin)  # negativo: el album art desborda el cuadro
    box = f"{width - 2 * inset}:{height - 2 * inset}"
    darken = _darken_filter(darkness)
    parts = []

    if background == "desenfocado":
        parts.append("[0:v]split[a][b]")
        parts.append(
            f"[a]scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},gblur=sigma={_blur_sigma(width, height):.1f},format=rgba{darken}[bg]"
        )
        source = "[b]"
    elif background == "personalizado":
        parts.append(
            f"[2:v]scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},format=rgba{darken}[bg]"
        )
        source = "[0:v]"
    elif background == "ninguno":
        parts.append(f"color=c=black:s={width}x{height}:r=1,format=rgba[bg]")
        source = "[0:v]"
    else:
        raise ValueError(f"Fondo desconocido: {background}")

    art = f"{source}scale={box}:force_original_aspect_ratio=decrease,format=rgba"
    if shadow:
        sigma, spread, pad, offset = _shadow_params(width, height)
        parts.append(f"{art},split[art][art_shadow]")
        parts.append(
            f"[art_shadow]colorchannelmixer=rr=0:gg=0:bb=0:aa={_SHADOW_OPACITY},"
            f"scale=iw+{2 * spread}:ih+{2 * spread},"
            f"pad=iw+{2 * pad}:ih+{2 * pad}:{pad}:{pad}:color=black@0,"
            f"gblur=sigma={sigma:.1f}[shadow]"
        )
        parts.append(f"[bg][shadow]overlay=(W-w)/2:(H-h)/2+{offset}:format=auto[base]")
        parts.append("[base][art]overlay=(W-w)/2:(H-h)/2:format=auto[framed]")
    else:
        parts.append(f"{art}[art]")
        parts.append("[bg][art]overlay=(W-w)/2:(H-h)/2:format=auto[framed]")

    last = "[framed]"
    if background != DEFAULT_BACKGROUND:
        # Un fondo desenfocado de una imagen transparente o una imagen de fondo con
        # transparencia también llevan alfa: se compone sobre negro.
        parts.append(f"color=c=black:s={width}x{height}:r=1,format=rgba[flat_base]")
        parts.append("[flat_base][framed]overlay=0:0:format=auto[flat]")
        last = "[flat]"

    parts.append(f"{last}{_OUTPUT},fps={fps}[v]")
    return ";".join(parts)


def render_preview(image, mode, width, height, background=DEFAULT_BACKGROUND,
                   shadow=False, margin=0, background_image=None, darkness=0):
    """Devuelve una imagen PIL de width x height con el mismo ajuste del video."""
    # Se trabaja en RGBA para conservar la transparencia; al final se compone sobre negro
    image = ImageOps.exif_transpose(image).convert("RGBA")
    size = (width, height)
    if mode == "cortar":
        return _flatten(ImageOps.fit(image, size, Image.LANCZOS)).convert("RGB")
    if mode == "estirar":
        return _flatten(image.resize(size, Image.LANCZOS)).convert("RGB")
    if mode != "ajustar":
        raise ValueError(f"Modo de ajuste desconocido: {mode}")

    if background == "desenfocado":
        canvas = ImageOps.fit(image, size, Image.LANCZOS)
        canvas = canvas.filter(ImageFilter.GaussianBlur(_blur_sigma(width, height)))
    elif background == "personalizado" and background_image is not None:
        canvas = ImageOps.fit(
            ImageOps.exif_transpose(background_image).convert("RGBA"), size, Image.LANCZOS)
    elif background in ("ninguno", "personalizado"):
        canvas = Image.new("RGBA", size, (0, 0, 0, 255))
    else:
        raise ValueError(f"Fondo desconocido: {background}")
    canvas = _flatten(canvas)
    if darkness and background != DEFAULT_BACKGROUND:
        canvas = _darken(canvas, darkness)

    inset = _inset(width, height, margin)  # negativo: el album art desborda el cuadro
    art = ImageOps.contain(image, (width - 2 * inset, height - 2 * inset), Image.LANCZOS)
    x, y = (width - art.width) // 2, (height - art.height) // 2

    if shadow:
        # La sombra sigue la silueta (canal alfa) del album art
        sigma, spread, pad, offset = _shadow_params(width, height)
        shadow_w, shadow_h = art.width + 2 * spread, art.height + 2 * spread
        silhouette = art.getchannel("A").resize((shadow_w, shadow_h), Image.LANCZOS)
        silhouette = silhouette.point(lambda value: round(value * _SHADOW_OPACITY))
        mask = Image.new("L", (shadow_w + 2 * pad, shadow_h + 2 * pad), 0)
        mask.paste(silhouette, (pad, pad))
        mask = mask.filter(ImageFilter.GaussianBlur(sigma))
        canvas.paste((0, 0, 0, 255), (x - spread - pad, y - spread - pad + offset), mask)

    # paste admite posiciones negativas (album art más grande que el cuadro) y usa el
    # alfa del album art como máscara
    result = canvas.convert("RGB")
    result.paste(art, (x, y), art)
    return result


def _darken(image, darkness):
    """Multiplica el color por (1 - oscuridad), igual que el filtro de FFmpeg."""
    rgb = ImageEnhance.Brightness(image.convert("RGB")).enhance(1 - darkness / 100)
    return rgb.convert("RGBA")


def _flatten(image):
    """Compone una imagen RGBA sobre negro (el MP4 no admite transparencia)."""
    return Image.alpha_composite(Image.new("RGBA", image.size, (0, 0, 0, 255)), image)
