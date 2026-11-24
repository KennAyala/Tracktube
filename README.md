> **Note:** this project was created with the assistance of artificial intelligence (Claude, by Anthropic). The code and documentation were generated and reviewed together with a person.

# Tracktube

A Python desktop app that turns **an image + an audio file into an MP4 video**, ready to upload to YouTube. It is built to export quickly, using the encoding settings recommended by YouTube.

Reference: [Recommended upload encoding settings](https://support.google.com/youtube/answer/1722171).

## Features

- Two simple inputs: **Album art** (jpg, jpeg, png, bmp) and **Audio track** (wav, flac, mp3, ogg), with buttons to add, replace and delete, plus drag and drop.
- Live **preview** of the frame that will fill the whole video.
- **PNG transparency is preserved:** transparent areas show the selected background (black when there is none), because MP4 has no alpha channel. The shadow follows the album art silhouette.
- **Aspect ratios:** 1:1, 4:3, 5:4 and 16:9, with **horizontal** (default) and **vertical** orientation buttons (3:4, 4:5 and 9:16).
- **Resolutions:** 480p, 720p, 1080p, 1440p and 2160p (4K). Resolution is taken from the short side.
- **FPS:** Minimum (1), 15, 24, 30 and 60 (default).
- **Image fit:** Fit, Crop or Stretch.
- With *Fit*: **background** (none, blurred album art or a custom image), album art **shadow** and a **margin** that moves the album art away from the edge.
- Editable **export path** (default `exports/{uuid}.mp4`), a button to change the folder and a refresh button that generates a new UUID. The UUID changes every time the app opens and after each export; a file name you typed yourself is kept.
- Warns you before exporting if a video already exists at the chosen path and will be replaced.
- Progress bar with its status (Ready, Exporting, Done) and a cancel button.
- **YouTube Short warning** when the video lasts 3:00 or less and the aspect ratio is not horizontal.
- Interface in **English** (default) and **Spanish**.
- Remembers your settings (options and export path) between sessions.
- **Log** panel for debugging, opened from the button at the top of the window and shown on the side.

## Requirements

- Python 3.11 or newer (developed and tested with 3.11).
- Windows (see [Known limitations](#known-limitations)).
- FFmpeg does not need to be installed: the binary ships with the `imageio-ffmpeg` package.

Dependencies (see [requirements.txt](requirements.txt)): PySide6, imageio-ffmpeg, mutagen, Pillow and pytest.

## Installation

```powershell
git clone https://github.com/KennAyala/tracktube.git
cd tracktube
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Why a virtual environment?

You need Python installed, but its libraries (PySide6, Pillow, ...) are not part of it. `python -m venv .venv` uses your Python to create a `.venv` folder with an isolated copy of it, and the install step puts the dependencies there so they do not mix with other projects. `.\.venv\Scripts\python.exe` is simply the Python inside that folder, so it can run the app without activating anything.

If you prefer, you can skip the virtual environment and install the dependencies in your own Python (`python -m pip install -r requirements.txt`), then run `python main.py`. You can also activate the environment first (`.\.venv\Scripts\Activate.ps1`) and use `python main.py`.

## Usage

```powershell
.\.venv\Scripts\python.exe main.py
```

Basic flow:

1. Add an image in **Album art** and an audio file in **Audio track**.
2. Choose aspect ratio, orientation, resolution, FPS and image fit.
3. Check the **Preview**.
4. Confirm the export path and click **Export**.

## Exported video specifications

| Item | Value |
|---|---|
| Container | MP4 with `faststart` |
| Video | H.264 (`libx264`), High profile, progressive, 2 B-frames, closed GOP, CABAC |
| GOP | Half the frame rate (minimum 1) |
| Color | `yuv420p`, BT.709 |
| Audio | AAC-LC stereo, 48 kHz, 384 kbps |

Video bitrate (SDR) by resolution and frame rate:

| Resolution | Up to 30 fps | 48–60 fps |
|---|---|---|
| 480p | 2.5 Mbps | 4 Mbps |
| 720p | 5 Mbps | 7.5 Mbps |
| 1080p | 8 Mbps | 12 Mbps |
| 1440p | 16 Mbps | 24 Mbps |
| 2160p | 40 Mbps | 60 Mbps |

Dimensions are computed from the short side and rounded to even numbers (a `yuv420p` requirement). Examples at 1080p: 16:9 → 1920×1080, 4:3 → 1440×1080, 5:4 → 1350×1080, 1:1 → 1080×1080, 9:16 → 1080×1920.

## Saved settings

Options and the export path are stored with `QSettings` (on Windows, in the registry under `HKEY_CURRENT_USER\Software\Tracktube`). If the saved path uses a UUID as its file name, a new UUID is assigned every time the app starts so the previous export is not overwritten; a name typed by hand is kept.

## Project structure

```
tracktube/
├─ main.py                  # entry point
├─ requirements.txt
├─ pytest.ini
├─ exports/                 # default export folder
├─ tracktube/
│  ├─ config.py             # allowed extensions and base paths
│  ├─ i18n.py               # translations (en / es)
│  ├─ log.py                # debug logger
│  ├─ core/
│  │  ├─ presets.py         # ratios, resolutions, fps, bitrates
│  │  ├─ fit_modes.py       # image fit: FFmpeg filter + Pillow preview
│  │  ├─ ffmpeg_cmd.py      # builds the FFmpeg command
│  │  ├─ exporter.py        # runs FFmpeg, progress and cancellation
│  │  ├─ export_path.py     # default export path and folder change
│  │  └─ media_info.py      # audio duration and image validation
│  └─ ui/
│     ├─ main_window.py
│     ├─ file_slot.py       # file input (add, replace, delete)
│     ├─ preview_widget.py
│     ├─ export_worker.py   # export thread
│     └─ log_panel.py       # log panel
└─ tests/
```

## QA and testing

### Automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

What they cover:

| File | Covers |
|---|---|
| `test_presets.py` | Even and correct dimensions per ratio and resolution, orientation, bitrates, GOP and the YouTube Short rule |
| `test_fit_modes.py` | FFmpeg filters and Pillow preview for each fit, background, shadow and margin |
| `test_exporter.py` | Real exports: checks H.264 High, `yuv420p`, BT.709, size, fps, AAC 48 kHz stereo, progress, cancellation and logging |
| `test_export_path.py` | Default path, relative path resolution, `.mp4` extension and folder change |
| `test_main_window.py` | UI (headless): UUID renewal on start and after exporting, refresh button, overwrite confirmation |
| `test_media_info.py` | Transparency detection for PNG images |
| `test_i18n.py` | Same keys in English and Spanish, default language |
| `test_log.py` | Message forwarding to the log panel |

### Manual checklist

- [ ] Add, replace and delete the image and the audio (with the buttons and by dragging).
- [ ] The preview updates when changing ratio, orientation, fit, background, shadow and margin.
- [ ] A PNG with transparency shows the background through its transparent areas (no white box) in the thumbnail, the preview and the exported video.
- [ ] Switching to vertical renames the ratio selector entries to 3:4, 4:5 and 9:16.
- [ ] The ✕ button next to the margin resets it to 0.
- [ ] The Short warning shows for audio of 3:00 or less in 1:1 or vertical, and hides in horizontal or above 3:00.
- [ ] Switching between English and Spanish translates the whole interface.
- [ ] Closing and reopening the app keeps the settings and export path.
- [ ] The UUID in the export path changes when the app opens, after each export and when clicking the refresh button.
- [ ] Exporting to a path that already exists shows a warning with Replace and Cancel; Cancel leaves the file untouched.
- [ ] Export, cancel halfway, and export again.
- [ ] Open the resulting MP4 and confirm it matches the preview.
- [ ] The **Log** button at the top opens the panel on the right, and it shows the FFmpeg command and progress.

## Known limitations

- Only tested on Windows. The code has no known Windows-only dependencies, but other systems have not been tried.
- Bitrate values are taken from YouTube's recommendations and should be checked against the official documentation from time to time.
- With 60 fps and high resolutions (for example 4K), encoding long audio files takes noticeably longer.
- There is no `.exe` packaging yet.

## License

To be defined.
