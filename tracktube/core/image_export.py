from pathlib import Path

IMAGE_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}

JPG_FILTER = "JPG (*.jpg *.jpeg)"
PNG_FILTER = "PNG (*.png)"
IMAGE_FILTERS = f"{JPG_FILTER};;{PNG_FILTER}"  # JPG va primero: es el formato por defecto


def resolve_image_path(path, selected_filter=""):
    """Devuelve la ruta final de la imagen.

    La extensión escrita (.jpg, .jpeg o .png) manda; si falta o no es válida se usa
    el filtro elegido en el diálogo (JPG por defecto).
    """
    path = Path(path)
    if path.suffix.lower() in IMAGE_FORMATS:
        return path
    extension = ".png" if selected_filter.startswith("PNG") else ".jpg"
    return path.with_name(path.name + extension)


def save_image(image, path):
    """Guarda una imagen PIL como JPG (calidad 95) o PNG según la extensión de `path`."""
    path = Path(path)
    image_format = IMAGE_FORMATS[path.suffix.lower()]
    image = image.convert("RGB")
    if image_format == "JPEG":
        image.save(path, "JPEG", quality=95, subsampling=0)
    else:
        image.save(path, "PNG", optimize=True)
