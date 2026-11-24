"""Modos de ajuste de la imagen al cuadro del video.

Cada modo tiene dos implementaciones equivalentes:
- build_filter_graph: filtro de FFmpeg para el video final.
- render_preview: la misma lógica con Pillow para el preview de la UI.

Los fondos, la sombra y el margen solo aplican al modo "ajustar".
"""

import math

from PIL import Image, ImageFilter, ImageOps

FIT_MODES = ("ajustar", "cortar", "estirar")
DEFAULT_FIT_MODE = "ajustar"

BACKGROUNDS = ("ninguno", "desenfocado", "personalizado")
DEFAULT_BACKGROUND = "ninguno"

# Margen del album art respecto al borde, en % del lado corto
MAX_MARGIN = 40

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


def build_filter_graph(mode, width, height, fps, background=DEFAULT_BACKGROUND,
                       shadow=False, margin=0):
    """Devuelve el filter_complex de FFmpeg con salida etiquetada [v].

    El input se lee a 1 fps y `fps` duplica el frame al final, así los
    filtros pesados solo se ejecutan una vez por segundo.
    El fondo "personalizado" toma su imagen del input [2:v].
    """
    size = f"{width}:{height}"
    if mode == "ajustar":
        if background == DEFAULT_BACKGROUND and not shadow and margin == 0:
            chain = (
                f"[0:v]scale={size}:force_original_aspect_ratio=decrease,"
                f"pad={size}:(ow-iw)/2:(oh-ih)/2:black,"
            )
        else:
            return _build_framed_graph(width, height, fps, background, shadow, margin)
    elif mode == "cortar":
        chain = (
            f"[0:v]scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},"
        )
    elif mode == "estirar":
        chain = f"[0:v]scale={size},"
    else:
        raise ValueError(f"Modo de ajuste desconocido: {mode}")
    return f"{chain}{_OUTPUT},fps={fps}[v]"


def _build_framed_graph(width, height, fps, background, shadow, margin):
    size = f"{width}:{height}"
    inset = _inset(width, height, margin)
    box = f"{width - 2 * inset}:{height - 2 * inset}"
    parts = []

    if background == "desenfocado":
        parts.append("[0:v]split[a][b]")
        parts.append(
            f"[a]scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},gblur=sigma={_blur_sigma(width, height):.1f},format=rgba[bg]"
        )
        source = "[b]"
    elif background == "personalizado":
        parts.append(
            f"[2:v]scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},format=rgba[bg]"
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

    parts.append(f"[framed]{_OUTPUT},fps={fps}[v]")
    return ";".join(parts)


def render_preview(image, mode, width, height, background=DEFAULT_BACKGROUND,
                   shadow=False, margin=0, background_image=None):
    """Devuelve una imagen PIL de width x height con el mismo ajuste del video."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    size = (width, height)
    if mode == "cortar":
        return ImageOps.fit(image, size, Image.LANCZOS)
    if mode == "estirar":
        return image.resize(size, Image.LANCZOS)
    if mode != "ajustar":
        raise ValueError(f"Modo de ajuste desconocido: {mode}")

    if background == "desenfocado":
        canvas = ImageOps.fit(image, size, Image.LANCZOS)
        canvas = canvas.filter(ImageFilter.GaussianBlur(_blur_sigma(width, height)))
    elif background == "personalizado" and background_image is not None:
        canvas = ImageOps.fit(
            ImageOps.exif_transpose(background_image).convert("RGB"), size, Image.LANCZOS)
    elif background in ("ninguno", "personalizado"):
        canvas = Image.new("RGB", size, (0, 0, 0))
    else:
        raise ValueError(f"Fondo desconocido: {background}")

    inset = _inset(width, height, margin)
    art = ImageOps.contain(image, (width - 2 * inset, height - 2 * inset), Image.LANCZOS)
    x, y = (width - art.width) // 2, (height - art.height) // 2

    if shadow:
        sigma, spread, pad, offset = _shadow_params(width, height)
        shadow_w, shadow_h = art.width + 2 * spread, art.height + 2 * spread
        mask = Image.new("L", (shadow_w + 2 * pad, shadow_h + 2 * pad), 0)
        mask.paste(round(255 * _SHADOW_OPACITY), (pad, pad, pad + shadow_w, pad + shadow_h))
        mask = mask.filter(ImageFilter.GaussianBlur(sigma))
        canvas.paste((0, 0, 0), (x - spread - pad, y - spread - pad + offset), mask)

    canvas.paste(art, (x, y))
    return canvas
