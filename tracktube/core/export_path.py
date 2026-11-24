import uuid
from pathlib import Path

from tracktube.config import BASE_DIR, DEFAULT_EXPORT_DIR


def new_default_path():
    """Ruta por defecto: exports/{uuid}.mp4 (relativa a la carpeta de la app)."""
    return f"{DEFAULT_EXPORT_DIR}/{uuid.uuid4()}.mp4"


def resolve_path(text):
    """Convierte el texto del input en una ruta absoluta y asegura la extensión .mp4."""
    path = Path(text.strip())
    if not path.is_absolute():
        path = BASE_DIR / path
    if path.suffix.lower() != ".mp4":
        path = path.with_name(path.name + ".mp4")
    return path


def change_folder(text, folder):
    """Cambia solo la carpeta de la ruta, conservando el nombre del archivo."""
    return str(Path(folder) / Path(text.strip()).name)
