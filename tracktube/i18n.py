"""Traducciones de la interfaz (inglés por defecto y español)."""

LANGUAGES = {"en": "English", "es": "Español"}
DEFAULT_LANGUAGE = "en"

STRINGS = {
    "en": {
        "header.language": "Language",
        "slot.image": "Album art",
        "slot.audio": "Audio track",
        "slot.empty": "No file selected",
        "slot.add": "Add",
        "slot.replace": "Replace",
        "slot.remove": "Delete",
        "slot.image_info": "{width} × {height} px",
        "slot.audio_info": "Duration: {duration}",
        "preview.title": "Preview",
        "preview.empty": "No image selected",
        "settings.title": "Settings",
        "settings.ratio": "Aspect ratio",
        "settings.horizontal": "Horizontal",
        "settings.vertical": "Vertical",
        "settings.resolution": "Resolution",
        "settings.fit": "Image fit",
        "fit.ajustar": "Fit",
        "fit.cortar": "Crop",
        "fit.estirar": "Stretch",
        "settings.background": "Background",
        "background.ninguno": "None",
        "background.desenfocado": "Blurred album art",
        "background.personalizado": "Custom",
        "settings.choose_background": "Choose image…",
        "settings.background_dialog": "Background image",
        "settings.shadow": "Add shadow to album art",
        "settings.margin": "Margin",
        "settings.margin_tip": "Distance between the album art and the edge of the video",
        "settings.fps": "FPS",
        "settings.fps_min": "Minimum ({fps} fps)",
        "export.title": "Export",
        "export.path": "Export path",
        "export.change_folder": "Change folder",
        "export.folder_dialog": "Export folder",
        "export.button": "Export",
        "export.cancel": "Cancel",
        "export.idle": "Ready",
        "export.running": "Exporting…",
        "export.done": "Done",
        "msg.no_path": "Enter the export path.",
        "msg.no_background": "Choose a background image or change the background option.",
        "msg.exported": "Video exported:\n{path}",
        "msg.open_folder": "Open folder",
        "msg.export_failed": "Could not export the video:\n{error}",
        "error.image_read": "Could not read the image: {error}",
        "error.audio_read": "Could not read the audio: {error}",
    },
    "es": {
        "header.language": "Idioma",
        "slot.image": "Carátula",
        "slot.audio": "Pista de audio",
        "slot.empty": "Ningún archivo seleccionado",
        "slot.add": "Agregar",
        "slot.replace": "Reemplazar",
        "slot.remove": "Eliminar",
        "slot.image_info": "{width} × {height} px",
        "slot.audio_info": "Duración: {duration}",
        "preview.title": "Vista previa",
        "preview.empty": "Ninguna imagen seleccionada",
        "settings.title": "Ajustes",
        "settings.ratio": "Aspect ratio",
        "settings.horizontal": "Horizontal",
        "settings.vertical": "Vertical",
        "settings.resolution": "Resolución",
        "settings.fit": "Ajuste de imagen",
        "fit.ajustar": "Ajustar",
        "fit.cortar": "Cortar",
        "fit.estirar": "Estirar",
        "settings.background": "Fondo",
        "background.ninguno": "Ninguno",
        "background.desenfocado": "Carátula desenfocada",
        "background.personalizado": "Personalizado",
        "settings.choose_background": "Elegir imagen…",
        "settings.background_dialog": "Imagen de fondo",
        "settings.shadow": "Agregar sombra a la carátula",
        "settings.margin": "Margen",
        "settings.margin_tip": "Distancia entre la carátula y el borde del video",
        "settings.fps": "FPS",
        "settings.fps_min": "Mínimo ({fps} fps)",
        "export.title": "Exportar",
        "export.path": "Ruta de exportación",
        "export.change_folder": "Cambiar carpeta",
        "export.folder_dialog": "Carpeta de exportación",
        "export.button": "Exportar",
        "export.cancel": "Cancelar",
        "export.idle": "Listo",
        "export.running": "Exportando…",
        "export.done": "Completado",
        "msg.no_path": "Indica la ruta de exportación.",
        "msg.no_background": "Elige una imagen de fondo o cambia la opción de fondo.",
        "msg.exported": "Video exportado:\n{path}",
        "msg.open_folder": "Abrir carpeta",
        "msg.export_failed": "No se pudo exportar el video:\n{error}",
        "error.image_read": "No se pudo leer la imagen: {error}",
        "error.audio_read": "No se pudo leer el audio: {error}",
    },
}

_language = DEFAULT_LANGUAGE


def set_language(code):
    global _language
    _language = code if code in LANGUAGES else DEFAULT_LANGUAGE


def get_language():
    return _language


def tr(key, **params):
    text = STRINGS[_language].get(key) or STRINGS[DEFAULT_LANGUAGE].get(key, key)
    return text.format(**params) if params else text
