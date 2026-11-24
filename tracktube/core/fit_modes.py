"""Modos de ajuste de la imagen al cuadro del video.

Cada modo tiene dos implementaciones equivalentes:
- build_filter_graph: filtro de FFmpeg para el video final.
- render_preview: la misma lógica con Pillow para el preview de la UI.
"""

from PIL import Image, ImageFilter, ImageOps

FIT_MODES = {
    "ajustar": "Ajustar",
    "cortar": "Cortar",
    "estirar": "Estirar",
    "desenfocado": "Ajustar con fondo desenfocado",
}
DEFAULT_FIT_MODE = "ajustar"

# Conversión final: BT.709 rango limitado, yuv420p (como pide YouTube)
_OUTPUT = "setsar=1,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"


def _blur_sigma(width, height):
    return max(1, min(width, height) / 25)


def build_filter_graph(mode, width, height, fps):
    """Devuelve el filter_complex de FFmpeg con salida etiquetada [v].

    El input se lee a 1 fps y `fps` duplica el frame al final, así los
    filtros pesados solo se ejecutan una vez por segundo.
    """
    size = f"{width}:{height}"
    if mode == "ajustar":
        chain = (
            f"[0:v]scale={size}:force_original_aspect_ratio=decrease,"
            f"pad={size}:(ow-iw)/2:(oh-ih)/2:black,"
        )
    elif mode == "cortar":
        chain = (
            f"[0:v]scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},"
        )
    elif mode == "estirar":
        chain = f"[0:v]scale={size},"
    elif mode == "desenfocado":
        sigma = _blur_sigma(width, height)
        chain = (
            f"[0:v]split[a][b];"
            f"[a]scale={size}:force_original_aspect_ratio=increase,"
            f"crop={size},gblur=sigma={sigma:.1f}[bg];"
            f"[b]scale={size}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        )
    else:
        raise ValueError(f"Modo de ajuste desconocido: {mode}")
    return f"{chain}{_OUTPUT},fps={fps}[v]"


def render_preview(image, mode, width, height):
    """Devuelve una imagen PIL de width x height con el mismo ajuste del video."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    size = (width, height)
    if mode == "ajustar":
        return ImageOps.pad(image, size, Image.LANCZOS, color=(0, 0, 0))
    if mode == "cortar":
        return ImageOps.fit(image, size, Image.LANCZOS)
    if mode == "estirar":
        return image.resize(size, Image.LANCZOS)
    if mode == "desenfocado":
        background = ImageOps.fit(image, size, Image.LANCZOS)
        background = background.filter(
            ImageFilter.GaussianBlur(_blur_sigma(width, height))
        )
        foreground = ImageOps.contain(image, size, Image.LANCZOS)
        background.paste(
            foreground,
            ((width - foreground.width) // 2, (height - foreground.height) // 2),
        )
        return background
    raise ValueError(f"Modo de ajuste desconocido: {mode}")
