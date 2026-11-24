> **Nota:** este proyecto fue creado con asistencia de inteligencia artificial (Claude, de Anthropic). El código y la documentación fueron generados y revisados en conjunto con una persona.

# Tracktube

Aplicación de escritorio en Python para convertir **una imagen + un audio en un video MP4**, listo para subir a YouTube. Está pensada para exportar rápido, con las características de codificación que recomienda YouTube.

Referencia usada: [Configuración de codificación recomendada para subir videos](https://support.google.com/youtube/answer/1722171).

## Características

- Dos entradas simples: **Album art** (jpg, jpeg, png, bmp) y **Audio track** (wav, flac, mp3, ogg), con botones para agregar, reemplazar y eliminar, y soporte de arrastrar y soltar.
- **Preview** en vivo de cómo se verá el frame que ocupará todo el video.
- **Aspect ratios:** 1:1, 4:3, 5:4 y 16:9, con botones de orientación **horizontal** (por defecto) y **vertical** (3:4, 4:5 y 9:16).
- **Resoluciones:** 480p, 720p, 1080p, 1440p y 2160p (4K). La resolución se toma por el lado corto.
- **FPS:** Mínimo (1), 15, 24, 30 y 60 (por defecto).
- **Ajuste de imagen:** Ajustar, Cortar o Estirar.
- Con el ajuste *Ajustar*: **fondo** (ninguno, carátula desenfocada o imagen personalizada), **sombra** para la carátula y **margen** que aleja la carátula del borde.
- **Ruta de exportación** editable (por defecto `exports/{uuid}.mp4`) y botón para cambiar la carpeta.
- Barra de progreso, botón de cancelar y aviso al terminar con acceso a la carpeta.
- **Aviso de YouTube Short** cuando el video dura 3:00 o menos y el aspect ratio no es horizontal.
- Interfaz en **inglés** (por defecto) y **español**.
- Guarda tu configuración (ajustes y ruta de exportación) entre sesiones.
- Panel **Log** de depuración al fondo de la ventana.

## Requisitos

- Python 3.11 o superior (desarrollado y probado con 3.11).
- Windows (ver [Limitaciones conocidas](#limitaciones-conocidas)).
- No hace falta instalar FFmpeg: el binario viene incluido con el paquete `imageio-ffmpeg`.

Dependencias (ver [requirements.txt](requirements.txt)): PySide6, imageio-ffmpeg, mutagen, Pillow y pytest.

## Instalación

```powershell
git clone https://github.com/KennAyala/tracktube.git
cd tracktube
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Ejecución

```powershell
.\.venv\Scripts\python.exe main.py
```

Uso básico:

1. Agrega una imagen en **Album art** y un audio en **Audio track**.
2. Elige aspect ratio, orientación, resolución, FPS y el ajuste de imagen.
3. Revisa el **Preview**.
4. Confirma la ruta de exportación y pulsa **Exportar**.

## Especificaciones del video exportado

| Elemento | Valor |
|---|---|
| Contenedor | MP4 con `faststart` |
| Video | H.264 (`libx264`), perfil High, progresivo, 2 B-frames, GOP cerrado, CABAC |
| GOP | La mitad del frame rate (mínimo 1) |
| Color | `yuv420p`, BT.709 |
| Audio | AAC-LC estéreo, 48 kHz, 384 kbps |

Bitrate de video (SDR) según resolución y frame rate:

| Resolución | Hasta 30 fps | 48–60 fps |
|---|---|---|
| 480p | 2.5 Mbps | 4 Mbps |
| 720p | 5 Mbps | 7.5 Mbps |
| 1080p | 8 Mbps | 12 Mbps |
| 1440p | 16 Mbps | 24 Mbps |
| 2160p | 40 Mbps | 60 Mbps |

Las dimensiones se calculan a partir del lado corto y se redondean a números pares (requisito de `yuv420p`). Ejemplos a 1080p: 16:9 → 1920×1080, 4:3 → 1440×1080, 5:4 → 1350×1080, 1:1 → 1080×1080, 9:16 → 1080×1920.

## Configuración guardada

Los ajustes y la ruta de exportación se guardan con `QSettings` (en Windows, en el registro bajo `HKEY_CURRENT_USER\Software\Tracktube`). Si la ruta guardada tenía un nombre generado (uuid), al abrir la app se asigna uno nuevo para no sobrescribir la exportación anterior; un nombre escrito a mano se respeta.

## Estructura del proyecto

```
tracktube/
├─ main.py                  # punto de entrada
├─ requirements.txt
├─ pytest.ini
├─ exports/                 # carpeta de exportación por defecto
├─ tracktube/
│  ├─ config.py             # extensiones permitidas y rutas base
│  ├─ i18n.py               # traducciones (en / es)
│  ├─ log.py                # logger de depuración
│  ├─ core/
│  │  ├─ presets.py         # ratios, resoluciones, fps, bitrates
│  │  ├─ fit_modes.py       # ajuste de imagen: filtro FFmpeg + preview con Pillow
│  │  ├─ ffmpeg_cmd.py      # arma el comando de FFmpeg
│  │  ├─ exporter.py        # ejecuta FFmpeg, progreso y cancelación
│  │  ├─ export_path.py     # ruta de exportación por defecto y cambio de carpeta
│  │  └─ media_info.py      # duración del audio y validación de imagen
│  └─ ui/
│     ├─ main_window.py
│     ├─ file_slot.py       # entrada de archivo (agregar, reemplazar, eliminar)
│     ├─ preview_widget.py
│     ├─ export_worker.py   # hilo de exportación
│     └─ log_panel.py       # panel de log
└─ tests/
```

## QA y pruebas

### Pruebas automáticas

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Qué cubren:

| Archivo | Cubre |
|---|---|
| `test_presets.py` | Dimensiones pares y correctas por ratio y resolución, orientación, bitrates, GOP y regla del aviso de Short |
| `test_fit_modes.py` | Filtros de FFmpeg y preview con Pillow para cada ajuste, fondo, sombra y margen |
| `test_exporter.py` | Exportaciones reales: verifica H.264 High, `yuv420p`, BT.709, tamaño, fps, AAC 48 kHz estéreo, progreso, cancelación y log |
| `test_export_path.py` | Ruta por defecto, resolución de rutas relativas, extensión `.mp4` y cambio de carpeta |
| `test_i18n.py` | Mismas claves en inglés y español, idioma por defecto |
| `test_log.py` | Reenvío de mensajes al panel de log |

### Lista de verificación manual

- [ ] Agregar, reemplazar y eliminar imagen y audio (por botón y arrastrando).
- [ ] El preview cambia al variar ratio, orientación, ajuste, fondo, sombra y margen.
- [ ] Al cambiar a vertical, los nombres del selector pasan a 3:4, 4:5 y 9:16.
- [ ] El botón ✕ del margen lo regresa a 0.
- [ ] El aviso de Short aparece con un audio de 3:00 o menos en 1:1 o vertical, y desaparece en horizontal o con más de 3:00.
- [ ] Cambiar entre inglés y español traduce toda la interfaz.
- [ ] Cerrar y abrir la app conserva ajustes y ruta de exportación.
- [ ] Exportar, cancelar a mitad y volver a exportar.
- [ ] Abrir el MP4 resultante y confirmar que coincide con el preview.
- [ ] El panel **Log** muestra el comando de FFmpeg y el progreso.

## Limitaciones conocidas

- Solo se ha probado en Windows. El botón "Abrir carpeta" usa `os.startfile`, que no existe en otros sistemas.
- Los valores de bitrate están tomados de las recomendaciones de YouTube y conviene contrastarlos de vez en cuando con la documentación oficial.
- Con 60 fps y resoluciones altas (por ejemplo 4K) la codificación de audios largos tarda bastante más.
- Aún no hay empaquetado a `.exe`.

## Licencia

Pendiente de definir.
