import sys
from pathlib import Path

APP_NAME = "Tracktube"

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")
AUDIO_EXTENSIONS = (".wav", ".flac", ".mp3", ".ogg")

# Carpeta base de la app: junto al .exe si está empaquetada, o la raíz del proyecto.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_EXPORT_DIR = "exports"

ICON_PATH = BASE_DIR / "assets" / "logo.png"
