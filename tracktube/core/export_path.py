import uuid
from pathlib import Path

from tracktube.config import BASE_DIR


def new_default_filename():
    """Nombre de archivo por defecto: {uuid}.mp4"""
    return f"{uuid.uuid4()}.mp4"


def resolve_path(text):
    """Convierte el texto en una ruta absoluta y asegura la extensión .mp4."""
    path = Path(text.strip())
    if not path.is_absolute():
        path = BASE_DIR / path
    if path.suffix.lower() != ".mp4":
        path = path.with_name(path.name + ".mp4")
    return path


def build_path(folder, filename):
    """Une la carpeta y el nombre de archivo (la carpeta relativa parte de la app)."""
    return resolve_path(str(Path(folder.strip()) / filename.strip()))
